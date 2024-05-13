"""Persistent configuration stored in standard user data directories"""
from enum import Enum
import os
import platform
import yaml
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict


def _platform_data_dir() -> Path:
    if platform.system() == "Windows":
        return Path(os.environ["LOCALAPPDATA"])
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home)
        return Path.home() / ".local" / "share"


data_dir = _platform_data_dir() / "shroudstone"
data_dir.mkdir(parents=True, exist_ok=True)
config_file = data_dir / "config.yaml"

DEFAULT_1v1_FORMAT = "{time:%Y-%m-%d %H.%M} {result:.1} {duration} {us} {f1:.1}v{f2:.1} {them} - {map_name}.SGReplay"
DEFAULT_GENERIC_FORMAT = "{time:%Y-%m-%d %H.%M} {duration} {players_with_factions} - {map_name}.SGReplay"
"""Default format string for new 1v1 replay filenames"""


class Config(BaseModel):
    replay_dir: Optional[Path] = None
    replay_name_format_1v1: str = DEFAULT_1v1_FORMAT
    replay_name_format_generic: str = DEFAULT_GENERIC_FORMAT
    minimize_to_tray: bool = False
    show_log_on_autorename: bool = False

    @staticmethod
    def load():
        if config_file.exists():
            with config_file.open("rt", encoding="utf-8") as f:
                content = yaml.load(f, Loader=yaml.SafeLoader)
                # Migrate old configs:
                if "replay_name_format" in content:
                    content["replay_name_format_1v1"] = content["replay_name_format"]
                return Config.model_validate(content)
        else:
            config = Config()
            config.save()
            return config

    def save(self):
        with config_file.open("wt", encoding="utf-8") as f:
            yaml.dump(self.model_dump(mode="json"), f, width=float("inf"))

    model_config = ConfigDict(extra="ignore")
