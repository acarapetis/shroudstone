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

### On Windows: .exe download

Simply [download the latest standalone executable](https://github.com/acarapetis/shroudstone/releases/latest/download/shroudstone.exe)
and double-click it to launch the user interface.

### On Windows: Using pip

1. Install Python 3.11 using
   [the Microsoft Store](https://apps.microsoft.com/detail/9nrwmjp3717k) or the
   [official installer](https://www.python.org/downloads/). If using the
   official installer, make sure to check the "add python.exe to PATH" option.
2. Open Command Prompt and type `pip install shroudstone` to install shroudstone.
3. You can now invoke `python -m shroudstone gui` from the command line to
   launch the user interface, or `python -m shroudstone --help` for usage
   instructions for the command-line interface.

You should also be able to get it working using a non-UWP python install, or
using WSL - just `pip install shroudstone` and you should be good to go.

### On Linux: using pip

If you're running Stormgate on Linux+Steam+Proton, this should also work for
you!

1. Ensure python 3.8+ and pip are installed using your system package manager.
   (e.g. on Ubuntu, run `sudo apt install python3-pip`.)
2. Run `pip install shroudstone` in a terminal.
3. Launch the GUI with `shroudstone gui`, or check out `shroudstone --help` if
   you want to use the CLI.

### Updating

Regardless of your operating system, if you installed using `pip install
shroudstone` originally, you can update to the newest version with a simple
`pip install --upgrade shroudstone`.


If you downloaded the .exe, just download a new one to replace it!


## Notes

- Shroudstone can currently only rename 1v1 ladder games - this is because it
  relies on the Stormgate World API to fetch most of its information.
- Stormgate names your replays using your local time. After renaming, the times
  will be in the UTC timezone, as on the Stormgate World leaderboard.
- Your settings are saved in %LOCALAPPDATA%/shroudstone/config.json on Windows
  or ~/.local/share/shroudstone/config.json on Linux/WSL. Note that if you're
  using Python from the Microsoft Store, this %LOCALAPPDATA% might not be
  what you expect - use `python -m shroudstone config-path` to find out exactly
  where it is.
- If using the CLI, Your player ID, replay directory path and replay format
  string can be configured by passing command-line options to `python -m
  shroudstone rename-replays`; but you probably want to use the config file
  instead so you don't have to provide them every time. Use `python -m
  shroudstone edit-config` to edit the configuration file.


## Customizing replay names

You can customize the filenames of your renamed replays by editing the format
string in your config file. (Use `python -m shroudstone edit-config` to open
the config file in a text editor, or click the "Edit Config File" button in the
GUI.)

The default format string is

     {time:%Y-%m-%d %H.%M} {result:.1} {duration} {us} {r1:.1}v{r2:.1} {them} - {map_name}.SGReplay

which results in e.g.

      2024-02-03 08.28 L 03m03s Pox IvI Veni Vidi Vici - Broken Crown.SGReplay

Note the usage of `:.1` to take just the first letter of the race and result strings.

Format strings can use the following values:

* `us` (str): Your nickname
* `them` (str): Opponent nickname
* `r1` (str): Race/faction you played (Vanguard or Infernals)
* `r2` (str): Race/faction opponent played
* `time` (datetime): Creation time of match
* `duration` (str): Game duration (e.g. "15m10s")
* `result` (str): Your game result (Win, Loss, Undecided)
* `map_name` (str): Name of the map on which the game was played (extracted from replay file)
* `build_number` (int): Build number of Stormgate version on which the game was played (extracted from replay file)


## Contributing

Contributions are welcome - feel free to open a PR, or message Pox on the
Stormgate Discord if you want to discuss with me first.
