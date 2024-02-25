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

1. Install Python 3.11 using
   [the Microsoft Store](https://apps.microsoft.com/detail/9nrwmjp3717k) or the
   [official installers](https://www.python.org/downloads/).
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

### Updating

Regardless of your operating system, if you installed using `pip install
shroudstone` originally, you can update to the newest version with a simple
`pip install --upgrade shroudstone`.


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
- Your player ID, replay directory path and replay format string can be
  configured by passing command-line options to `python -m shroudstone
  rename-replays`; but you probably want to use the config file instead so you
  don't have to provide them every time. Use `python -m shroudstone
  edit-config` to edit the configuration file.


## Customizing replay names

You can customize the filenames of your renamed replays by editing the format
string in your config file. (Use `python -m shroudstone edit-config` to open
the config file in a text editor.)

The default format string is

     {time:%Y-%m-%d %H.%M} {result:.1} {duration} {us} {r1:.1}v{r2:.1} {them} - {map_name}.SGReplay

which results in e.g.

      2024-02-03 08.28 L 03m03s Pox IvI Veni Vidi Vici - Broken Crown.SGReplay

Note the usage of `:.1` to take just the first letter of the race and result strings.

Format strings can use the following values:

* `us` (str): Your nickname
* `them` (str): Opponent nickname
* `r1` (str): Race/faction you played (Vanguard or Infernal)
* `r2` (str): Race/faction opponent played
* `time` (datetime): Creation time of match
* `duration` (str): Game duration (e.g. "15m10s")
* `result` (str): Your game result (Win, Loss, Unknown)
* `map_name` (str): Name of the map on which the game was played (extracted from replay file)


## Contributing

Contributions are welcome - feel free to open a PR, or message Pox on the
Stormgate Discord if you want to discuss with me first.
