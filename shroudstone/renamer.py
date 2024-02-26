"""Rename stormgate replays to include useful info in filename"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import logging
from shutil import copytree
from time import sleep
from typing import List, NamedTuple, Optional
from urllib.request import urlopen, Request

import pandas as pd

from shroudstone.replay import get_match_info
from shroudstone.config import data_dir
from shroudstone import __version__

logger = logging.getLogger(__name__)

STORMGATEWORLD = "https://api.stormgateworld.com"

TOLERANCE = timedelta(seconds=90)
"""Maximum time difference to consider games a match"""

BAD_CHARS = re.compile(r'[<>:"/\\|?*\0]')
"""Characters forbidden in filenames on Linux or Windows"""

USER_AGENT = f"shroudstone v{__version__}"
"""User-Agent to use in requests to the API"""

cache_dir = data_dir / "stormgateworld-cache"
"""Directory in which match data is cached"""


def rename_replays(
    replay_dir: Path,
    my_player_id: str,
    format: str,
    dry_run: bool = False,
    backup: bool = True,
    reprocess: bool = False,
    check_nicknames: bool = True,
):
    if dry_run:
        # Don't bother
        bu_dir = None
        logger.warning(
            "Performing a dry run - will show what would happen but not actually touch anything."
        )
    elif backup:
        bu_dir = replay_dir.parent / f"{replay_dir.name}.backup"
        backup_dir(replay_dir, bu_dir)
    else:
        bu_dir = None
        logger.warning("No backup being made! You asked for it!")

    if reprocess:
        # Reprocess all replays
        pattern = "**/*.SGReplay"
        logger.info(f"Searching for all replays in {replay_dir}.")
    else:
        # Only look for replays we haven't already renamed
        pattern = "**/CL*.SGReplay"
        logger.info(f"Searching for unrenamed replays in {replay_dir}.")

    replays = [
        x for x in map(ReplayFile.from_path, replay_dir.glob(pattern)) if x is not None
    ]
    if not replays:
        logger.warning(
            "No replays found to rename! "
            f"If you weren't expecting this, check your replay_dir '{replay_dir}' is correct."
        )
        return

    n = len(replays)
    earliest_time = min(x.time for x in replays)
    logger.info(f"Found {n} unrenamed replays going back to {earliest_time}.")
    matches = get_player_matches(my_player_id)

    for r in replays:
        try:
            match = find_match(matches, r, check_nicknames=check_nicknames)
        except NicknameMismatch as e:
            logger.error(
                f"Found time-based match for {r.path.name} "
                f"but nicknames didn't match: {e.leaderboard_nicknames} != {e.replay_nicknames}. "
                "Provide --no-check-nicknames to turn off this check and accept this as a match anyway."
            )
        except NoMatch:
            info = get_match_info(r.path)
            if len(info.player_nicknames) == 1:
                nick = info.player_nicknames[0]
                logger.info(
                    f"No match found for {r.path.name}. Only one player was found ({nick})"
                    ", so this is probably a match vs AI."
                )
            else:
                logger.warning(
                    f"No match found for {r.path.name} in stormgateworld match history."
                    "Could be a custom game?"
                )
        else:
            try:
                rename_replay(r, match, dry_run=dry_run, format=format)
            except Exception as e:
                logger.error(f"Unexpected error handling {r.path}: {e}")

    if bu_dir:
        logger.warning(
            f"Renaming completed. Your replays were backed up to {bu_dir}. "
            "Please check that nothing went wrong now - subsequent runs will overwrite your backup!"
        )


def backup_dir(replay_dir: Path, bu_dir: Path):
    logger.warning(
        f"Backing up your replays to {bu_dir}. "
        "Please check the results after this run - subsequent runs will overwrite your backup! "
    )
    copytree(replay_dir, bu_dir, dirs_exist_ok=True)


def naive_localtime_to_utc(dt: datetime) -> datetime:
    assert dt.tzinfo is None
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class ReplayFile(NamedTuple):
    path: Path
    time: datetime

    @staticmethod
    def from_path(path: Path):
        # Original names use local times:
        if m := re.search(r"(\d\d\d\d)\.(\d\d)\.(\d\d)-(\d\d).(\d\d)", path.name):
            time = naive_localtime_to_utc(
                datetime(*(int(x) for x in m.groups()))  # type: ignore
            )
        # Our renamed versions use UTC:
        elif m := re.search(r"(\d\d\d\d)-(\d\d)-(\d\d) (\d\d).(\d\d)", path.name):
            time = datetime(*(int(x) for x in m.groups()))  # type: ignore
        else:
            return None
        return ReplayFile(path, time)


def clear_cached_matches(player_id: str):
    logger.info(f"Clearing local match cache.")
    cache_file = cache_dir / f"{player_id}.csv"
    cache_file.unlink(missing_ok=True)


def load_cached_matches(player_id: str) -> Optional[pd.DataFrame]:
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache_file = cache_dir / f"{player_id}.csv"
    if cache_file.exists():
        return pd.read_csv(
            cache_file, parse_dates=["created_at", "ended_at"], index_col="match_id"
        )


def save_cached_matches(player_id: str, matches: pd.DataFrame):
    logger.info(f"Saving {len(matches)} matches to local cache.")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache_file = cache_dir / f"{player_id}.csv"
    matches.to_csv(cache_file, index=True)


def get_player_matches(player_id: str, reset_cache: bool = False):
    """Get the complete set of matches for the player of interest.

    We make the assumption that matches are only ever added going forward in
    time, allowing us to start with the most recent matches and request back
    only as far as required until we hit the last cached match."""
    cached_matches = load_cached_matches(player_id)
    if cached_matches is None:
        last_cached_match_time = datetime(1970, 1, 1, 0, 0, 0)
        n = 0
        logger.info(
            f"No local match cache found for {player_id}, requesting complete match history."
        )
    else:
        last_cached_match_time = cached_matches.created_at.max()
        n = len(cached_matches)
        logger.info(
            f"Loaded {n} matches from local cache, most recent dated {last_cached_match_time}."
        )

    page = 1
    logger.info(
        f"Requesting most recent matches for {player_id} from Stormgate World API."
    )
    matches = fetch_player_matches_page(player_id, page=page)
    if matches is None:
        raise Exception(
            "Could not find any matches for {player_id=} - check this player_id is correct!"
        )
    # Add an hour's padding to avoid any weird edge cases
    while matches.created_at.min() > last_cached_match_time - timedelta(hours=1):
        sleep(1)  # Be nice to the API servers! You can wait a few seconds!
        logger.info(
            f"Got matches back to {matches.created_at.min()}, requesting next page from API."
        )
        page += 1
        next_page = fetch_player_matches_page(player_id, page=page)
        if next_page is None:
            break
        matches = pd.concat([matches, next_page])
    if cached_matches is not None:
        matches = pd.concat([cached_matches, matches])
        dups = matches.index.duplicated(keep="last")
        matches = matches[~dups]
    matches = matches.sort_values(["created_at", "match_id"])
    save_cached_matches(player_id, matches)
    return matches


def fetch_player_matches_page(player_id: str, page: int):
    request = Request(
        f"{STORMGATEWORLD}/v0/players/{player_id}/matches?page={page}",
        headers={"User-Agent": USER_AGENT},
    )
    with urlopen(request) as f:
        data = json.load(f)["matches"]
    if not data:
        return None
    data = [flatten_match(player_id, x) for x in data]
    matches = pd.json_normalize([x for x in data if x is not None])
    return matches.assign(
        ended_at=pd.to_datetime(matches["ended_at"]),
        created_at=pd.to_datetime(matches["created_at"]),
    ).set_index("match_id")


def flatten_match(player_id: str, match: dict):
    """Rewrite the players array as two keys `us` and `them`."""
    try:
        match["us"] = next(
            p for p in match["players"] if p["player"]["player_id"] == player_id
        )
        match["them"] = next(
            p for p in match["players"] if p["player"]["player_id"] != player_id
        )
    except Exception:
        return None
    del match["players"]
    return match


class NoMatch(Exception):
    pass


@dataclass
class NicknameMismatch(Exception):
    leaderboard_nicknames: List[str]
    replay_nicknames: List[str]


def find_match(matches: pd.DataFrame, replay: ReplayFile, check_nicknames: bool):
    """Given a replay file and a list of matches from stormgateworld, find the
    closest match in time with the correct nicknames."""
    delta = (matches.created_at - replay.time).abs()
    df = matches.assign(delta=delta)
    candidates = df[delta < TOLERANCE].sort_values("delta")
    for _, match in candidates.iterrows():
        info = get_match_info(replay.path)
        match["map_name"] = info.map_name or "UnknownMap"
        match["build_number"] = info.build_number

        if not check_nicknames:
            return match

        n1 = match.get("us.player.nickname")
        n2 = match.get("them.player.nickname")

        nickname_diff = {n1, n2}.symmetric_difference(info.player_nicknames)

        if not nickname_diff:
            return match
        else:
            ns1 = sorted([n1, n2])
            ns2 = sorted(info.player_nicknames)
            raise NicknameMismatch(ns1, ns2)

    raise NoMatch()


def rename_replay(replay: ReplayFile, match: pd.Series, dry_run: bool, format: str):
    parts = {}
    parts["us"] = match["us.player.nickname"]
    parts["them"] = match["them.player.nickname"]

    try:
        parts["r1"] = match["us.race"][0].capitalize()
    except Exception:
        parts["r1"] = "?"

    try:
        parts["r2"] = match["them.race"][0].capitalize()
    except Exception:
        parts["r2"] = "?"

    try:
        parts["result"] = match["us.result"].capitalize()
    except Exception:
        parts["result"] = "?"

    parts["map_name"] = match["map_name"]
    parts["build_number"] = match["build_number"]

    try:
        minutes, seconds = divmod(int(match["duration"]), 60)
        parts["duration"] = f"{minutes:02d}m{seconds:02d}s"
        parts["time"] = match["created_at"]
    except Exception:
        parts["duration"] = "??m??s"
        parts["time"] = replay.time.strftime("")

    try:
        newname = format.format(**parts)
        target = replay.path.parent / newname
        do_rename(replay.path, target, dry_run=dry_run)
    except Exception as e:
        logger.error(f"Unexpected error renaming {replay.path}: {e}")


def do_rename(source: Path, target: Path, dry_run: bool):
    if target.exists():
        logger.error(f"Not renaming {source}! {target} already exists!")
        return

    if dry_run:
        logger.info(f"DRY RUN: Would have renamed {source.name} => {target.name}.")
        return

    logger.info(f"Renaming {source.name} => {target.name}.")
    try:
        source.rename(target)
    except Exception as e:
        # In case the error was due to weird characters in a player name:
        new_name = sanitize_filename(target.name)
        if new_name != target.name:
            logger.warning(
                f"Error renaming {source} => {target.name}, retrying with sanitized filename."
            )
            do_rename(source, target.parent / new_name, dry_run=dry_run)
        else:
            logger.error(f"Error renaming {source} => {target.name}: {e}")


def sanitize_filename(filename: str) -> str:
    """Remove bad characters from a filename"""
    return BAD_CHARS.sub("", filename)
