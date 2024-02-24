# shroudstone

[![PyPI](https://img.shields.io/pypi/v/shroudstone)](https://pypi.org/project/shroudstone/)

Shroudstone is principally a tool to automatically rename replays of your
Stormgate ladder games.

Say goodbye to 

      CL44420-2024.02.03-08.28.SGReplay

and say hello to

      2024-02-03 08.28 L 03m03s Pox IvI Veni Vidi Vici - Broken Crown.SGReplay

Shroudstone also acts as a general Python/CLI toolkit for working with
Stormgate replays - right now it's probably not useful for much else, but
hopefully it will grow over time :)

Made possible by the great work of the [Stormgate
World](https://www.stormgateworld.com/) team!

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


## Notes

- Stormgate names your replays using your local time. After renaming, the times
  will be in the UTC timezone, as on the Stormgate World leaderboard.
- Your settings are saved in %LOCALAPPDATA%/shroudstone/config.json on Windows
  or ~/.local/share/shroudstone/config.json on Linux/WSL.
- Your player ID, replay directory path and replay format string can be
  configured by passing command-line options to `python -m shroudstone
  rename-replays`; but you probably want to use the config file instead so you
  don't have to provide them every time. Use `python -m shroudstone
  edit-config` to edit the configuration file.
