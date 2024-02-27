"""Persistent configuration stored in standard user data directories"""
import os
import platform
import yaml
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


def _platform_data_dir() -> Path:
    if platform.system() == "Windows":
        return Path(os.environ["LOCALAPPDATA"])
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home)
        return Path("~").expanduser() / ".local" / "share"


data_dir = _platform_data_dir() / "shroudstone"
data_dir.mkdir(parents=True, exist_ok=True)
config_file = data_dir / "config.yaml"

DEFAULT_FORMAT = "{time:%Y-%m-%d %H.%M} {result:.1} {duration} {us} {r1:.1}v{r2:.1} {them} - {map_name}.SGReplay"
"""Default format string for new replay filenames"""

class Config(BaseModel):
    my_player_id: Optional[str] = None
    replay_dir: Optional[Path] = None
    replay_name_format: str = DEFAULT_FORMAT

    @staticmethod
    def load():
        if config_file.exists():
            with config_file.open("rt") as f:
                content = yaml.load(f, Loader=yaml.SafeLoader)
                return Config.model_validate(content)
        else:
            return Config()

    def save(self):
        with config_file.open("wt") as f:
            yaml.dump(self.model_dump(mode="json"), f, width=float("inf"))
