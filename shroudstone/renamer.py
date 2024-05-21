"""Rename stormgate replays to include useful info in filename"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import os
import string
from pathlib import Path
import platform
import re
import logging
from shutil import copytree, rmtree
from typing import Iterable, NamedTuple, Optional, Union
from typing_extensions import Literal
from uuid import UUID
from packaging import version

from shroudstone import __version__
from shroudstone.replay import Player, ReplaySummary, summarize_replay, FRIGATE
from shroudstone.config import data_dir

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


VALID_FIELDS = {
    "1v1": [
        "us",
        "them",
        "f1",
        "f2",
        "r1", # for backwards compat
        "r2",
        "time",
        "duration",
        "result",
        "map_name",
        "build_number",
    ],
    "generic": [
        "players",
        "players_with_factions",
        "time",
        "duration",
        "map_name",
        "build_number",
    ]
}


def migrate():
    last_run_version_file = data_dir / "last_run_version.txt"
    if last_run_version_file.exists():
        last_run_version = version.parse(
            last_run_version_file.read_text(encoding="utf-8")
        )
    else:
        last_run_version = version.parse("0.1.0a29")
    if last_run_version < version.parse("0.1.0a30"):
        logger.info(
            "Cache files are from an incompatible version of shroudstone, deleting them."
        )
        skipped_replays_file.unlink(missing_ok=True)
        rmtree(cache_dir, ignore_errors=True)
    last_run_version_file.write_text(__version__, encoding="utf-8")


def rename_replays(
    replay_dir: Path,
    format_1v1: str,
    format_generic: str,
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

    def try_parse(path: Path):
        try:
            return Replay.from_path(path)
        except Exception:
            logger.exception(f"Unexpected error parsing {path}")

    replays = [x for x in map(try_parse, files) if x is not None]
    if not replays:
        logger.warning(
            "No new replays found to rename! "
            f"If you weren't expecting this, check your replay_dir '{replay_dir}' is correct."
        )
        return

    n = len(replays)
    earliest_time = min(x.time for x in replays)
    logger.info(f"Found {n} unrenamed replays going back to {earliest_time}.")
    if not skipped_replays_file.exists():
        skipped_replays_file.touch()
    previously_skipped_paths = {
        Path(x)
        for x in skipped_replays_file.read_text(encoding="utf-8").splitlines()
        if x
    }
    skipped_paths = []

    counts = defaultdict(lambda: 0)
    for replay in replays:
        if replay.path in previously_skipped_paths:
            counts["skipped_old"] += 1
            logger.debug(
                f"We've previously skipped {replay.path.name}, so not commenting on it this time."
            )
        elif any(p.is_ai for p in replay.summary.players):
                counts["skipped_new"] += 1
                skipped_paths.append(replay.path)
                logger.info(f"{replay.path.name} is a game vs AI, skipping it.")
                continue
        else:
            try:
                rename_replay(
                    replay,
                    dry_run=dry_run,
                    format_1v1=format_1v1,
                    format_generic=format_generic,
                )
                counts["renamed"] += 1
            except Exception as e:
                logger.error(f"Unexpected error handling {replay.path}: {e}")
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


class Replay(NamedTuple):
    path: Path
    summary: ReplaySummary
    time: datetime
    us: Optional[Player]
    them: Optional[Player]

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

        summary = summarize_replay(path)
        our_uuid = find_our_uuid(path)

        us = None
        them = None
        if len(summary.players) == 2:
            if summary.players[0].uuid == our_uuid:
                us, them = summary.players
            elif summary.players[1].uuid == our_uuid:
                them, us = summary.players
        elif len(summary.players) > 0 and summary.players[0].uuid == our_uuid:
            us = summary.players[0]

        return Replay(path=path, time=time, us=us, them=them, summary=summary)


def find_our_uuid(replay_path: Path) -> Optional[UUID]:
    """Given the path to a Stormgate replay, extract the player UUID. (This
    assumes it's stored in the usual directory heirarchy.)"""
    for part in reversed(replay_path.parts):
        try:
            return UUID(hex=part)
        except ValueError:
            pass


def get_result(replay: Replay):
    if not (replay.us and replay.them):
        return None
    if replay.summary.build_number >= FRIGATE:
        # Since Frigate we've had explicit surrender messages, so we rely on them alone for certainty:
        if replay.us.leave_reason == "surrender":
            return "loss"
        if replay.them.leave_reason == "surrender":
            return "win"
        return None
    else:
        # For old replays, best we can do is guess based on disconnection times:
        t1 = replay.us.disconnect_time
        t2 = replay.them.disconnect_time
        if t1 and t2:
            return "win" if t1 > t2 else "loss"
        elif t1:
            return "loss"
        elif t2:
            return "win"



def rename_replay(
    replay: Replay,
    dry_run: bool,
    format_1v1: str,
    format_generic: str,
):
    parts = {}
    parts["map_name"] = replay.summary.map_name
    parts["build_number"] = replay.summary.build_number
    duration = replay.summary.duration_seconds
    if duration is not None:
        minutes, seconds = divmod(int(duration), 60)
        parts["duration"] = f"{minutes:02d}m{seconds:02d}s"
    else:
        parts["duration"] = ""

    parts["time"] = replay.time

    us = replay.us
    them = replay.them
    if us and them:
        # 1v1
        parts["us"] = parts["p1"] = us.nickname
        parts["them"] = parts["p2"] = them.nickname

        parts["r1"] = parts["f1"] = (us.faction or "").capitalize()
        parts["r2"] = parts["f2"] = (them.faction or "").capitalize()

        result = get_result(replay)
        parts["result"] = (result or "unknown").capitalize()

        newname = format_1v1.format(**parts)
    else:
        parts["players"] = ", ".join(
            p.nickname.capitalize() for p in replay.summary.players
        )
        parts["players_with_factions"] = ", ".join(
            f"{p.nickname.capitalize()} {(p.faction or '').upper():.1}" for p in replay.summary.players
        )
        newname = format_generic.format(**parts)

    # In case we left some blanks, collapse multiple spaces to one space
    newname = re.sub(r"\s+", " ", newname)

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
            Path.home()
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


def validate_format_string(format: str, type: Union[Literal["1v1"], Literal["generic"]]):
    parts = string.Formatter().parse(format)
    for _, field_name, _, _ in parts:
        if field_name is not None and field_name not in VALID_FIELDS[type]:
            raise ValueError(f"Unknown replay field {field_name}")
