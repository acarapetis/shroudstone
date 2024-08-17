"""Summarize Stormgate replays into a JSON schema."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import BinaryIO, List, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, PlainSerializer
from typing_extensions import Annotated, TypeVar

from .parser import Faction, GameState, LeftGameReason, get_build_number

logger = logging.getLogger(__name__)

# My empirical testing found that the timestamps in replays seem to be in units of ~0.976ms.
# This is very close to 1/1024 of a second, so we'll assume that this is the exact value.
REPLAY_TIMESTAMP_UNIT = 1 / 1024


T = TypeVar("T", bound=Enum)


def _from_name(t: Type[T]):
    def get(n: Union[str, T]) -> T:
        if isinstance(n, Enum):
            return n
        return getattr(t, n)

    return get


def _validator(t: Type[T]):
    return BeforeValidator(_from_name(t))


_serialize = PlainSerializer(lambda x: x.name, when_used="json-unless-none")


class InvalidGameState(Exception):
    """Replay parsed successfully, but we don't understand the final gamestate."""


class Spectator(BaseModel):
    nickname: str
    nickname_discriminator: Optional[str] = None
    uuid: Optional[UUID] = None


class Player(BaseModel):
    nickname: str
    nickname_discriminator: Optional[str] = None
    uuid: Optional[UUID] = None
    faction: Annotated[Optional[Faction], _validator(Faction), _serialize]
    is_ai: bool = False
    disconnect_time: Optional[float] = None
    leave_reason: Annotated[LeftGameReason, _validator(LeftGameReason), _serialize] = (
        LeftGameReason.Unknown
    )


class ReplaySummary(BaseModel):
    build_number: int
    map_name: Optional[str]
    players: List[Player] = []
    spectators: List[Spectator] = []
    duration_seconds: Optional[float] = None
    is_1v1_ladder_game: bool = False


def summarize_replay(replay: Union[Path, BinaryIO]) -> ReplaySummary:
    """Parse what we can from a stormgate replay."""
    build_number = get_build_number(replay)
    state = GameState.at_end_of(replay)
    info = ReplaySummary(
        build_number=build_number,
        map_name=state.map_name,
    )
    if state.game_started_time is not None:
        first_left_game_time = min(
            c.left_game_time or float("inf") for c in state.clients.values()
        )
        info.duration_seconds = (
            first_left_game_time - state.game_started_time
        ) * REPLAY_TIMESTAMP_UNIT
    for slot in state.slots.values():
        if slot.ai_type is not None:
            info.players.append(
                Player(
                    nickname=slot.ai_type.name,
                    is_ai=True,
                    faction=slot.faction,
                )
            )
        elif slot.client_id is not None:
            client = state.clients.pop(slot.client_id)
            if client.nickname is None:
                raise InvalidGameState(
                    f"No nickname found for client {client.client_id} = {client.uuid}?"
                )
            info.players.append(
                p := Player(
                    nickname=client.nickname,
                    nickname_discriminator=client.discriminator,
                    uuid=client.uuid,
                    is_ai=False,
                    faction=slot.faction,
                )
            )
            if (
                state.game_started_time is not None
                and client.left_game_time is not None
            ):
                p.disconnect_time = (
                    client.left_game_time - state.game_started_time
                ) * REPLAY_TIMESTAMP_UNIT
            p.leave_reason = client.left_game_reason
    for client in state.clients.values():
        if client.slot_number != 255:
            raise InvalidGameState("Player not in a slot but slot_number != 255?")
        if client.nickname is None:
            raise InvalidGameState(
                f"No nickname found for client {client.client_id} = {client.uuid}?"
            )
        info.spectators.append(
            Spectator(
                nickname=client.nickname,
                nickname_discriminator=client.discriminator,
                uuid=client.uuid,
            )
        )
    info.is_1v1_ladder_game = (  # TODO: Can we update this with the match type?
        len(info.players) == 2
        and len(info.spectators) == 0
        and len(state.slot_assignments) > 0
    )
    return info
