# shroudstone

Shroudstone is a command-line tool that automatically renames replays of
your Stormgate ladder games.

Say goodbye to `CL44420-2024.02.03-08.28.SGReplay` and say hello to `2024-02-03
08.28 L 03m03s Pox IvI Veni Vidi Vici - Broken Crown.SGReplay`.

Shroudstone also acts as a general Python + CLI toolkit for working with
Stormgate replays.

## Installation & Usage

### On Windows

1. Install Python 3.11 from the Microsoft Store.
2. Open Command Prompt and type `pip install shroudstone` to install shroudstone.
3. You can now invoke `python -m shroudstone rename-replays` from the command
   line to rename your replays. To avoid having to do this every time, `python
   -m shroudstone create-rename-replays-shortcut` will create an icon on your
   desktop so it's just a double-click away :)

You should also be able to get it working using a non-UWP python install, or
using WSL - just `pip install shroudstone` and you should be good to go.

### On Linux

If you're running Stormgate on Linux+Steam+Proton, hopefully this should also
work for you - just `pip install shroudstone` and give it a shot.
