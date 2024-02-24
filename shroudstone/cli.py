from pathlib import Path

import typer

from shroudstone import replay

app = typer.Typer()


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
