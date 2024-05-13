from __future__ import annotations
from datetime import datetime

from pathlib import Path
from typing import List, Optional
from uuid import UUID
from sqlalchemy import Dialect, ForeignKey, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, String


class PathString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[Path], dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value: Optional[str], dialect):
        return Path(value) if value is not None else None

    def copy(self, **kw):
        return PathString(self.impl.length)


class Base(DeclarativeBase):
    type_annotation_map = {Path: PathString}

    @declared_attr # type: ignore
    def __tablename__(cls):
        return cls.__name__.lower()


class Player(Base):
    """An actual human player."""
    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    nickname: Mapped[str]
    nickname_discriminator: Mapped[Optional[str]]


class ReplayFile(Base):
    """A stormgate match replay."""
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    md5sum: Mapped[str] = mapped_column(index=True)
    path: Mapped[Path]

    # This is determined from the filename when replays are first written out by Stormgate:
    started_at: Mapped[Optional[datetime]]

    # These fields are determined by parsing the replay:
    build_number: Mapped[int]
    map_name: Mapped[Optional[str]]
    duration_seconds: Mapped[Optional[float]]
    is_1v1_ladder_game: Mapped[bool]

    slots: Mapped[List[PlayerSlot]] = relationship()


class PlayerSlot(Base):
    """A player or spectator in a particular replay."""
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    replay_id: Mapped[int] = mapped_column(ForeignKey(ReplayFile.id))
    player_uuid: Mapped[Optional[UUID]] = mapped_column(ForeignKey(Player.uuid))

    # Two reasons to store nickname per-replay:
    # - Player nicknames can change
    # - AIs have nicknames
    nickname: Mapped[str]
    nickname_discriminator: Mapped[Optional[str]]

    is_spectator: Mapped[bool]
    faction: Mapped[Optional[str]]
    is_ai: Mapped[bool]
    disconnect_time: Mapped[Optional[float]]
    leave_reason: Mapped[str]

    replay: Mapped[ReplayFile] = relationship()
    player: Mapped[Optional[Player]] = relationship()


class RenameHistory(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    renamed_at: Mapped[datetime]
    old_path: Mapped[Path]
    new_path: Mapped[Path]
