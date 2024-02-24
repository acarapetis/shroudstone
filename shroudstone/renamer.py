"""Rename stormgate replays to include useful info in filename"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import logging
from shutil import copytree
from time import sleep
from typing import NamedTuple
from urllib.request import urlopen

import pandas as pd

from shroudstone.replay import get_match_info

logger = logging.getLogger(__name__)

STORMGATEWORLD = "https://api.stormgateworld.com"
TOLERANCE = timedelta(seconds=90)
"""Maximum time difference to consider games a match"""
BAD_CHARS = re.compile(r'[<>:"/\\|?*\0]')
"""Characters forbidden in filenames on Linux or Windows"""


def backup_dir(replay_dir: Path, bu_dir: Path):
    logger.warning(
        f"Backing up your replays to {bu_dir}. "
        "Please check the results after this run - subsequent runs will overwrite your backup!"
    )
    copytree(replay_dir, bu_dir, dirs_exist_ok=True)


def rename_replays(
    replay_dir: Path, my_player_id: str, dry_run: bool = False, backup: bool = True
):
    if backup:
        bu_dir = replay_dir.parent / f"{replay_dir.name}.backup"
        backup_dir(replay_dir, bu_dir)
    else:
        bu_dir = None
        logger.warning("No backup being made! You asked for it!")
    logger.info(f"Searching for unrenamed replays in {replay_dir}")
    unrenamed_replays = [
        x
        for x in map(ReplayFile.from_path, replay_dir.glob("**/CL*.SGReplay"))
        if x is not None
    ]
    if not unrenamed_replays:
        logger.warning(
            "No replays found to rename! "
            f"If you weren't expecting this, check your replay_dir '{replay_dir}' is correct."
        )
        return

    n = len(unrenamed_replays)
    earliest_time = min(x.time for x in unrenamed_replays)
    logger.info(
        f"Found {n} unrenamed replays going back to {earliest_time}. Fetching matches from stormgateworld now."
    )
    matches = player_matches_since(my_player_id, earliest_time)

    for r in unrenamed_replays:
        match = find_match(matches, r)
        if match is not None:
            try:
                rename_replay(r, match, dry_run=dry_run)
            except Exception as e:
                logger.error(f"Unexpected error handling {r.path}: {e}")
        else:
            logger.error(
                f"No match found for {r.path.name} in stormgateworld match history."
            )

    if bu_dir:
        logger.warning(
            f"Renaming completed. Your replays were backed up with to {bu_dir}. "
            "Please check that nothing went wrong now - subsequent runs will overwrite your backup!"
        )


class ReplayFile(NamedTuple):
    path: Path
    time: datetime

    @staticmethod
    def from_path(path: Path):
        m = re.search(r"(\d\d\d\d)\.(\d\d)\.(\d\d)-(\d\d).(\d\d)", path.name)
        if not m:
            return None
        time = (
            datetime(*(int(x) for x in m.groups()))  # type: ignore
            .astimezone()
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
        return ReplayFile(path, time)


def player_matches_since(player_id: str, time: datetime):
    page = 1
    matches = player_matches(player_id, page=page)
    if matches is None:
        raise Exception(
            "Could not find any matches for {player_id=} - check this is correct!"
        )
    while matches.created_at.min() > time:
        sleep(1)  # Be nice to the API servers! You can wait a few seconds!
        logger.info(f"Got matches back to {matches.created_at.min()}, going further.")
        page += 1
        next_page = player_matches(player_id, page=page)
        if next_page is None:
            logger.warning(
                f"Could only fetch back to {matches.created_at.min()} "
                "from stormgateworld but you have unrenamed replays from before this.",
            )
            return matches.reset_index(drop=True)
        matches = pd.concat([matches, next_page])
    return matches.reset_index(drop=True)


def player_matches(player_id: str, page: int):
    logger.info(f"Fetching match history page {page}...")
    url = f"{STORMGATEWORLD}/v0/players/{player_id}/matches?page={page}"
    with urlopen(url) as f:
        data = json.load(f)["matches"]
    if not data:
        return None
    data = [flatten_match(player_id, x) for x in data]
    matches = pd.json_normalize([x for x in data if x is not None])
    matches["ended_at"] = pd.to_datetime(matches["ended_at"])
    matches["created_at"] = pd.to_datetime(matches["created_at"])
    return matches


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


def find_match(matches: pd.DataFrame, replay: ReplayFile):
    """Given a replay file and a list of matches from stormgateworld, find the
    closest match in time with the correct nicknames."""
    delta = (matches.created_at - replay.time).abs()
    df = matches.assign(delta=delta)
    candidates = df[delta < TOLERANCE].sort_values("delta")
    for _, match in candidates.iterrows():
        if nicknames_match(replay, match):
            return match
        else:
            try:
                n1 = match["us.player.nickname"]
                n2 = match["them.player.nickname"]
            except Exception:
                n1 = "?"
                n2 = "?"
            logger.error(
                f"Found time-based match for {replay.path.name} but couldn't find "
                f"nicknames {n1!r}, {n2!r} in the replay!"
            )
            info = get_match_info(replay.path)
            logger.error(f"{info=}")


def nicknames_match(replay: ReplayFile, match: pd.Series):
    """Given a replay file and a match from the sgw API, check that the player
    nicknames match, and tack on the map name."""
    info = get_match_info(replay.path)
    try:
        match["map_name"] = info.map_name
    except Exception:
        pass
    try:
        p1 = match["us.player.nickname"]
        p2 = match["them.player.nickname"]
        return {p1, p2} == set(info.player_nicknames)
    except Exception:
        logger.exception("Error checking nicknames")
        return False


def rename_replay(replay: ReplayFile, match: pd.Series, dry_run: bool):
    us = match["us.player.nickname"]
    them = match["them.player.nickname"]

    try:
        r1 = match["us.race"][0].upper()
    except Exception:
        r1 = "?"

    try:
        r2 = match["them.race"][0].upper()
    except Exception:
        r2 = "?"

    try:
        result = match["us.result"][0].upper()
    except Exception:
        result = "?"

    try:
        map_name = match["map_name"]
    except Exception:
        map_name = "Unknown Map"

    try:
        minutes, seconds = divmod(int(match["duration"]), 60)
        duration = f"{minutes:02d}m{seconds:02d}s"
        time = match["created_at"].strftime("%Y-%m-%d %H.%M")
    except Exception:
        duration = "??m??s"
        time = replay.time.strftime("%Y-%m-%d %H.%M")

    try:
        newname = (
            f"{time} {result} {duration} {us} {r1}v{r2} {them} - {map_name}.SGReplay"
        )
        target = replay.path.parent / newname
        do_rename(replay.path, target, dry_run=dry_run)
    except Exception as e:
        logger.error(f"Unexpected error renaming {replay.path}: {e}")


def do_rename(source: Path, target: Path, dry_run: bool):
    if target.exists():
        logger.error(f"Not renaming {source}! {target.name} already exists!")
        return

    if dry_run:
        logger.info("DRY RUN: Would have renamed {source} => {target.name}.")
        return

    logger.info(f"Renaming {source} => {target.name}.")
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
