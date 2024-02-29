"""Rename stormgate replays to include useful info in filename"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import os
import string
from pathlib import Path
import platform
import re
import logging
from shutil import copytree, rmtree
from time import sleep
from typing import Iterable, NamedTuple, Optional
from uuid import UUID
from packaging import version

import pandas as pd

from shroudstone import __version__
from shroudstone.replay import get_match_info
from shroudstone.config import data_dir
from shroudstone.sgw_api import PlayersApi
from shroudstone.stormgateworld.models import PlayerResponse

logger = logging.getLogger(__name__)


TOLERANCE = timedelta(seconds=90)
"""Maximum time difference to consider games a match"""

BAD_CHARS = re.compile(r'[<>:"/\\|?*\0]')
"""Characters forbidden in filenames on Linux or Windows"""

cache_dir = data_dir / "stormgateworld-cache"
"""Directory in which match data is cached"""

uuid_dir = cache_dir / "by_uuid"
"""Directory in which UUID -> player_id mapping is cached"""

skipped_replays_file = data_dir / "skipped_replays.txt"
"""Directory in which previouslyskipped replays are recorded"""


FIELDS = [
    "us",
    "them",
    "r1",
    "r2",
    "time",
    "duration",
    "result",
    "map_name",
    "build_number",
]


def migrate():
    last_run_version_file = data_dir / "last_run_version.txt"
    if last_run_version_file.exists():
        last_run_version = version.parse(last_run_version_file.read_text(encoding="utf-8"))
    else:
        last_run_version = version.parse("0.1.0a29")
    if last_run_version < version.parse("0.1.0a30"):
        logger.info("Cache files are from an incompatible version of shroudstone, deleting them.")
        skipped_replays_file.unlink(missing_ok=True)
        rmtree(cache_dir)
    last_run_version_file.write_text(__version__, encoding="utf-8")


def rename_replays(
    replay_dir: Path,
    my_player_id: str,
    format: str,
    dry_run: bool = False,
    backup: bool = True,
    reprocess: bool = False,
    files: Optional[Iterable[Path]] = None,
):
    migrate()
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

    if files is None:
        if reprocess:
            # Reprocess all replays
            pattern = "**/*.SGReplay"
            logger.info(f"Searching for all replays in {replay_dir}.")
        else:
            # Only look for replays we haven't already renamed
            pattern = "**/CL*.SGReplay"
            logger.info(f"Searching for unrenamed replays in {replay_dir}.")

        files = replay_dir.glob(pattern)

    replays = [x for x in map(ReplayFile.from_path, files) if x is not None]
    if not replays:
        logger.warning(
            "No new replays found to rename! "
            f"If you weren't expecting this, check your replay_dir '{replay_dir}' is correct."
        )
        return

    n = len(replays)
    earliest_time = min(x.time for x in replays)
    logger.info(f"Found {n} unrenamed replays going back to {earliest_time}.")
    matches = get_player_matches(my_player_id)
    if not skipped_replays_file.exists():
        skipped_replays_file.touch()
    previously_skipped_paths = {
        Path(x) for x in skipped_replays_file.read_text(encoding="utf-8").splitlines() if x
    }
    skipped_paths = []

    counts = defaultdict(lambda: 0)
    for r in replays:
        try:
            match = find_match(matches, r)
        except MatchOngoing:
            logger.info(
                f"Found match for {r.path.name}, but it's still marked as ongoing - we'll rename it later."
            )
            counts["skipped_ongoing"] += 1
        except NoMatch:
            if r.path in previously_skipped_paths:
                counts["skipped_old"] += 1
                logger.debug(
                    f"We've previously skipped {r.path.name}, so not commenting on it this time."
                )
            else:
                counts["skipped_new"] += 1
                skipped_paths.append(r.path)
                info = get_match_info(r.path)
                if len(info.players) == 1:
                    nick = info.players[0].nickname
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
                counts["renamed"] += 1
            except Exception as e:
                logger.error(f"Unexpected error handling {r.path}: {e}")
                counts["error"] += 1

    if not dry_run:
        with skipped_replays_file.open("at", encoding="utf-8") as f:
            for path in skipped_paths:
                print(path, file=f)

    prefix = "DRY RUN: " if dry_run else ""
    counts_str = (
        "{renamed} replays renamed, "
        "{skipped_new} skipped (no matching ladder game), "
        "{skipped_ongoing} skipped (ongoing), "
        "{skipped_old} ignored (previously skipped), "
        "{error} errors."
    ).format_map(counts)
    logger.info(prefix + counts_str)


def backup_dir(replay_dir: Path, bu_dir: Path):
    logger.info(f"Backing up your replays to {bu_dir}.")
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


def get_player_by_uuid(uuid: UUID) -> PlayerResponse:
    uuid_dir.mkdir(exist_ok=True, parents=True)
    cache_file = uuid_dir / f"{uuid}.json"
    if cache_file.exists():
        player = PlayerResponse.model_validate_json(cache_file.read_text(encoding="utf-8"))
    else:
        player = PlayersApi.get_player(str(uuid))
        cache_file.write_text(player.model_dump_json(indent=2), encoding="utf-8")
    return player


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


def get_player_matches(player_id: str):
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
    # Don't cache incomplete data from ongoing matches:
    save_cached_matches(player_id, matches[matches["state"] != "ongoing"])
    return matches


def fetch_player_matches_page(player_id: str, page: int):
    # This is inefficient - we're converting JSON to pydantic then back to JSON
    # - but not gonna bother optimizing unless it's actually slow
    data = (
        PlayersApi.get_player_matches(player_id, page=page)
        .model_dump(mode="json")
        .get("matches")
    )
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


class MatchOngoing(Exception):
    pass


def find_match(matches: pd.DataFrame, replay: ReplayFile):
    """Given a replay file and a list of matches from stormgateworld, find the
    closest match in time with the correct players."""
    delta = (matches.created_at - replay.time).abs()
    df = matches.assign(delta=delta)
    candidates = df[delta < TOLERANCE].sort_values("delta")
    for _, match in candidates.iterrows():
        match_player_ids = {
            match.get("us.player.player_id"),
            match.get("them.player.player_id"),
        }
        info = get_match_info(replay.path)
        replay_players = [get_player_by_uuid(p.uuid) for p in info.players]

        if match_player_ids == {p.id for p in replay_players}:
            if match["state"] == "ongoing":
                raise MatchOngoing()

            # Add extra data from replay before returning match
            # TODO: Return this data in a more sensible class (or just a dict?)
            match["map_name"] = info.map_name or "UnknownMap"
            match["build_number"] = info.build_number
            if replay_players[0].id == match["us.player.player_id"]:
                us, them = info.players[0], info.players[1]
            else:
                us, them = info.players[1], info.players[0]
            match["us.replay_nickname"] = us.nickname
            match["them.replay_nickname"] = them.nickname

            return match

    raise NoMatch()


def rename_replay(replay: ReplayFile, match: pd.Series, dry_run: bool, format: str):
    parts = {}
    parts["us"] = match["us.replay_nickname"]
    parts["them"] = match["them.replay_nickname"]

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

    newname = format.format(**parts)
    target = replay.path.parent / newname
    do_rename(replay.path, target, dry_run=dry_run)


def do_rename(source: Path, target: Path, dry_run: bool):
    if source == target:
        logger.debug(f"{source} already has the desired format, doing nothing :)")
        return

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


def guess_replay_dir() -> Optional[Path]:
    if platform.system() == "Windows":
        # Should be easy, just look in the current user's local app data
        appdata = os.environ["LOCALAPPDATA"]
        paths = [Path(appdata) / "Stormgate" / "Saved" / "Replays"]
    else:
        # If this script is running on Linux and Stormgate is installed using
        # Steam+Proton, look in the steam compatdata:
        steammnt = (
            Path("~").expanduser()
            / ".steam/root/steamapps/compatdata/2012510/pfx/dosdevices"
        )

        # If this script is running on the Windows Subsystem for Linux, we can
        # find the Windows drives mounted in /mnt:
        wslmnt = Path("/mnt")

        tail = "AppData/Local/Stormgate/Saved/Replays"
        paths = [
            *steammnt.glob(f"*/users/steamuser/{tail}"),
            *wslmnt.glob(f"*/Users/*/{tail}"),
            *wslmnt.glob(f"*/Documents and Settings/*/{tail}"),
        ]

    for path in paths:
        if path.is_dir():
            return path


def guess_player_uuid(replay_dir: Path) -> Optional[UUID]:
    uuids = []
    for d in replay_dir.iterdir():
        if d.is_dir():
            try:
                uuids.append(UUID(d.name))
            except ValueError:
                pass
    if len(uuids) == 1:
        return uuids[0]


def guess_player(replay_dir: Path) -> Optional[PlayerResponse]:
    uuid = guess_player_uuid(replay_dir)
    if not uuid:
        return None
    try:
        return get_player_by_uuid(uuid)
    except Exception:
        return None


def validate_format_string(format: str):
    parts = string.Formatter().parse(format)
    for _, field_name, _, _ in parts:
        if field_name is not None and field_name not in FIELDS:
            raise ValueError(f"Unknown replay field {field_name}")
