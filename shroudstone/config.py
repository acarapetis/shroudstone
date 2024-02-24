"""Persistent configuration stored in standard user data directories"""
import os
import platform
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
config_file = data_dir / "config.json"


class Config(BaseModel):
    my_player_id: Optional[str] = None
    replay_dir: Optional[Path] = None

    @staticmethod
    def load():
        if config_file.exists():
            return Config.model_validate_json(config_file.read_text())
        else:
            return Config()

    def save(self):
        config_file.write_text(self.model_dump_json(indent=2))
