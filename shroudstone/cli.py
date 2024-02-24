"""The shroudstone CLI"""

import logging
import os
from pathlib import Path
import platform
import subprocess
from typing import Annotated, Optional

from rich.console import Console
from rich.logging import RichHandler
import typer

from shroudstone import renamer, replay
from shroudstone.config import Config, config_file, DEFAULT_FORMAT

app = typer.Typer()

console = Console(stderr=True)
logging.captureWarnings(True)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console)],
)
logger = logging.getLogger(__name__)


@app.command()
def get_replay_info(replay_file: typer.FileBinaryRead):
    """Extract information from a replay, outputting it in JSON format."""
    typer.echo(replay.get_match_info(replay_file).model_dump_json(indent=2))


@app.command()
def split_replay(replay_file: typer.FileBinaryRead, output_directory: Path):
    """Extract a stormgate replay into a directory containing individual protoscope messages."""
    output_directory.mkdir(exist_ok=True, parents=True)
    i = 0
    for i, chunk in enumerate(replay.split_replay(replay_file)):
        (output_directory / f"{i:07d}.binpb").write_bytes(chunk)
    typer.echo(
        f"Wrote {i+1} replay messages in protoscope wire format to {output_directory}/."
    )


@app.command()
def edit_config():
    """Open the shroudstone configuration file in your default text editor."""
    if not config_file.exists():
        Config().save()
    if platform.system() == "Windows":
        # .resolve() is crucial when python is installed from the microsoft store
        realpath = config_file.resolve()
        subprocess.run(["cmd", "/c", f"start {realpath}"])
    else:
        editor = os.environ.get("VISUAL", os.environ.get("EDITOR", "nano"))
        subprocess.run([editor, config_file.resolve()])


@app.command()
def create_rename_replays_shortcut():
    """Create a desktop icon to launch the rename-replays script."""
    if platform.system() != "Windows":
        logger.error("This subcommand is only currently available on Windows.")
    else:
        batch = (
            Path(os.environ["USERPROFILE"]) / "Desktop" / "Rename Stormgate Replays.bat"
        )
        with batch.open("wt") as f:
            print(
                """
@echo off
python -m shroudstone rename-replays
echo Press any key to close this window.
pause >nul
""",
                file=f,
            )
        logger.info(
            f"Batch file created at {batch} - should be visible on your desktop :)"
        )


@app.command()
def rename_replays(
    replay_dir: Annotated[
        Optional[Path],
        typer.Option(file_okay=False, dir_okay=True, exists=True, readable=True),
    ] = None,
    my_player_id: Optional[str] = None,
    format: Annotated[
        Optional[str], typer.Option(help=f"Format string for new replay filenames\n(e.g. '{DEFAULT_FORMAT}')")
    ] = None,
    backup: bool = True,
    dry_run: bool = False,
    reprocess: Annotated[
        bool, typer.Option(help="Reprocess old replays that have already been renamed")
    ] = False,
    check_nicknames: Annotated[
        bool,
        typer.Option(
            help="Check that nicknames in the replay match those from stormgateworld"
        ),
    ] = True,
):
    """Automatically rename your replay files (including player nicknames, races, map name, duration, result)"""
    config = Config.load()
    if replay_dir is None:
        replay_dir = get_replay_dir(config)
    if my_player_id is None:
        my_player_id = get_player_id(config)
    renamer.rename_replays(
        replay_dir=replay_dir,
        my_player_id=my_player_id,
        dry_run=dry_run,
        backup=backup,
        reprocess=reprocess,
        check_nicknames=check_nicknames,
        format=format or config.replay_name_format,
    )


def get_player_id(config: Config) -> str:
    if config.my_player_id is None:
        typer.echo(
            "You have not yet configured your player ID. To find it:\n"
            "1. visit https://stormgateworld.com/leaderboards/ranked_1v1 and search for your in-game nickname.\n"
            "2. find your account in the results and click on it.\n"
            "3. click the characters next to the '#' icon to copy your player ID.\n"
            "4. paste it below and press enter :)"
        )
        config.my_player_id = typer.prompt("Player ID")
    config.save()
    return config.my_player_id


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


def get_replay_dir(config: Config) -> Path:
    if config.replay_dir is None:
        config.replay_dir = guess_replay_dir()
        if config.replay_dir is None:
            typer.echo("Couldn't automatically determine your replay directory!")
            typer.echo(
                "It normally lives in your user directory under "
                r"AppData\Local\Stormgate\Saved\Replays."
            )
            typer.echo("If you know the correct path, please enter it now.")
            config.replay_dir = Path(typer.prompt("Path to replay directory"))
        config.save()
    return config.replay_dir
