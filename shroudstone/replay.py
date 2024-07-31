"""Stormgate replay parsing tools"""
from __future__ import annotations
from collections import defaultdict
from contextlib import contextmanager
from enum import IntEnum
import gzip
from pathlib import Path
import struct
from typing import BinaryIO, Dict, Iterable, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from . import stormgate_pb2 as pb

import logging

logger = logging.getLogger(__name__)


# My empirical testing found that the timestamps in replays seem to be in units of ~0.976ms.
# This is very close to 1/1024 of a second, so we'll assume that this is the exact value.
REPLAY_TIMESTAMP_UNIT = 1 / 1024

FRIGATE = 55366

@contextmanager
def decompress(replay: Union[Path, BinaryIO]):
    """Open a gzipped stormgate replay, skipping the 16-byte header."""
    if isinstance(replay, Path):
        replay = replay.open("rb")
    with replay:
        replay.seek(16)
        with gzip.GzipFile(fileobj=replay) as f2:
            yield f2


def get_build_number(replay: Union[Path, BinaryIO]) -> int:
    """Find the Stormgate version number that produced a given replay file.

    This is the number that can be found at the start of unrenamed replays,
    e.g. 44420 in CL44420-2024.01.31-16.23.SGReplay; but it is also stored in
    the 16-byte header, so we get it from there instead."""
    if isinstance(replay, Path):
        replay = replay.open("rb")
    replay.seek(12)
    (x,) = struct.unpack("<i", replay.read(4))
    replay.seek(0)
    return x


def read_varint(f) -> Optional[int]:
    """Read a base-7 varint from a binary stream, or return None if the stream is at EOF."""
    bs = f.read(1)
    if len(bs) == 0:
        return None
    byte = ord(bs)
    digits = byte & 0b01111111
    if byte & 0b10000000:
        nxt = read_varint(f)
        if nxt is None:
            raise ValueError("EOF encountered while parsing varint")
        digits += nxt << 7
    return digits


def split_replay(replay: Union[Path, BinaryIO]) -> Iterable[bytes]:
    """Split a replay into a sequence of chunks, each of which is a raw
    bytestring containing a wire-format encoding of a protobuf message."""
    with decompress(replay) as f:
        while True:
            length = read_varint(f)
            if length is None:
                break
            yield f.read(length)


class Spectator(BaseModel):
    nickname: str
    nickname_discriminator: Optional[str] = None
    uuid: Optional[UUID] = None


class Player(BaseModel):
    nickname: str
    nickname_discriminator: Optional[str] = None
    uuid: Optional[UUID] = None
    faction: Optional[str] = None
    is_ai: bool = False
    disconnect_time: Optional[float] = None
    leave_reason: str = "unknown"


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
                    faction=slot.faction.name,
                )
            )
        elif slot.client_id is not None:
            client = state.clients.pop(slot.client_id)
            info.players.append(
                p := Player(
                    nickname=client.nickname,
                    nickname_discriminator=client.discriminator,
                    uuid=client.uuid,
                    is_ai=False,
                    faction=slot.faction.name,
                )
            )
            if state.game_started_time is not None and client.left_game_time is not None:
                p.disconnect_time = (client.left_game_time - state.game_started_time)*REPLAY_TIMESTAMP_UNIT
            p.leave_reason = client.left_game_reason.name
    for client in state.clients.values():
        if client.slot_number != 255:
            raise ReplayParsingError("Player not in a slot but slot_number != 255?")
        info.spectators.append(
            Spectator(
                nickname=client.nickname,
                nickname_discriminator=client.discriminator,
                uuid=client.uuid,
            )
        )
    info.is_1v1_ladder_game = len(info.players) == 2 and len(info.spectators) == 0 and len(state.slot_assignments) > 0
    return info


# Unfortunately, to correctly determine who's in player slots and who's in
# spectator slots we need to know how many players the map has.
# For now, this is just 2 unless it's WreckHavoc.
player_slot_count: Dict[str, int] = defaultdict(lambda: 2, {"WreckHavoc": 3,"TheAbyssalGates" : 3})


class SlotType(IntEnum):
    closed = 0
    human = 1
    ai = 2


class Faction(IntEnum):
    vanguard = 0
    infernals = 1
    celestial = 2
    blockade = 101
    maloc = 201


class AIType(IntEnum):
    PeacefulBot = 0
    MurderBotJr = 1
    MurderBotSr = 2


class Slot(BaseModel):
    type: SlotType = SlotType.human
    faction: Faction = Faction(0)
    ai_type: Optional[AIType] = None
    client_id: Optional[int] = None


# The python protobuf bindings don't use standard python enums - they just return ints.
# I want nice type hints so I'm just going to maintain this manually.
class LeftGameReason(IntEnum):
    unknown = 0
    surrender = 1
    leave = 2


class Client(BaseModel):
    uuid: UUID
    client_id: int
    nickname: str
    discriminator: str
    slot_number: Optional[int] = None  # 255 means spectator
    left_game_time: Optional[float] = None
    left_game_reason: LeftGameReason = LeftGameReason.unknown


def parse_uuid(uuid: pb.UUID) -> UUID:
    return UUID(bytes=struct.pack(">qq", uuid.part1, uuid.part2))


class GameState(BaseModel):
    """Stormgate match state machine - reads commands from replay and updates state"""

    map_name: Optional[str] = None
    slots: Dict[int, Slot] = {}
    clients: Dict[int, Client] = {}
    slot_assignments: Dict[UUID, int] = {}
    game_started: bool = False
    game_started_time: Optional[float] = None

    @classmethod
    def at_end_of(cls, replay: Union[Path, BinaryIO]) -> GameState:
        """Simulate an entire replay and return the end state."""
        self = cls()
        for bytestring in split_replay(replay):
            chunk = pb.ReplayChunk.FromString(bytestring)
            self.process(chunk)
        return self

    def process(self, chunk: pb.ReplayChunk):
        """Update the state using a single replay chunk/command."""
        content = chunk.inner.content
        content_type = content.WhichOneof("content_type")
        handler = getattr(self, f"handle_{content_type}", None)
        if handler is not None:
            handler(
                getattr(content, content_type),
                client_id=chunk.client_id,
                timestamp=chunk.timestamp,
            )

    def handle_map(self, msg: pb.Map, **__):
        self.map_name = msg.name
        slot_count = player_slot_count[msg.name]
        logger.debug(f"Setting up {slot_count} slots for map {msg.name}")
        for i in range(1, slot_count + 1):
            self.slots[i] = Slot()

    def handle_assign_player_slot(self, msg: pb.AssignPlayerSlot, **__):
        self.slot_assignments[parse_uuid(msg.uuid)] = msg.slot
        logger.debug(f"Assigning slot {msg.slot} to {msg.uuid}")

    def handle_player(self, msg: pb.Player, client_id, **__):
        self.clients[client_id] = client = Client(
            client_id=client_id,
            uuid=parse_uuid(msg.uuid),
            nickname=msg.name.nickname,
            discriminator=msg.name.discriminator,
        )
        logger.debug(f"Setting up player {client_id}: {client.nickname} {client.uuid}")
        # If we're in a matchmaking game, the server has pre-assigned a slot for the player:
        if (slot_number := self.slot_assignments.get(client.uuid)) is not None:
            client.slot_number = slot_number
            self.slots[slot_number].client_id = client_id
            logger.debug(
                f"Putting player {client_id} in pre-assigned slot {slot_number}"
            )

    def handle_player_left_game(self, msg: pb.PlayerLeftGame, client_id, timestamp):
        if self.game_started:
            self.clients[client_id].left_game_time = timestamp
            self.clients[client_id].left_game_reason = LeftGameReason(msg.reason)
        else:
            client = self.clients.pop(client_id, None)
            # In aborted ladder games, we sometimes get a left game before the player joined message
            suffix = f": {client.nickname} {client.uuid}" if client is not None else ""
            logger.debug(f"Removing player {client_id}: {suffix}")
            for slot in self.slots.values():
                if slot.client_id == client_id:
                    slot.client_id = None

    def handle_change_slot(self, msg: pb.LobbyChangeSlot, client_id, **__):
        if not self.slots:
            raise ReplayParsingError("Received slot change before map info?")
        client = self.clients[client_id]
        if client.slot_number is not None and client.slot_number != 255:
            self.slots[client.slot_number].client_id = None
        if msg.choice.WhichOneof("choice_type") == "specific_slot":
            slot_number = msg.choice.specific_slot.slot
        else:
            # Client did not choose a specific slot, so they get the first open human slot
            for slot_number, slot in self.slots.items():
                if slot.type == SlotType.human and slot.client_id is None:
                    break
            else:
                # No open slots, become spectator
                slot_number = 255
        client.slot_number = slot_number
        if slot_number != 255:
            slot = self.slots[slot_number]
            if slot.type != SlotType.human:
                raise ReplayParsingError("Client assigned to non-human slot?")
            if slot.client_id is not None:
                raise ReplayParsingError("Client assigned to already occupied slot?")
            slot.client_id = client_id
            logger.debug(f"Putting player {client_id} in slot {slot_number}")

    def handle_set_variable(self, msg: pb.LobbySetVariable, **__):
        slot = self.slots[msg.slot]
        key = msg.variable_id
        value = msg.value
        if key == 374945738:
            slot.type = SlotType(value)
            logger.debug(f"Set slot[{msg.slot}].type = {slot.type}")
            if slot.type == SlotType.ai:
                slot.ai_type = AIType(0)
                logger.debug(f"Set slot[{msg.slot}].ai_type = {slot.ai_type}")
            else:
                slot.ai_type = None
                logger.debug(f"Set slot[{msg.slot}].ai_type = None")
        elif key == 2952722564:
            slot.faction = Faction(value)
            logger.debug(f"Set slot[{msg.slot}].faction = {slot.faction}")
        elif key == 655515685:
            slot.ai_type = AIType(value)
            logger.debug(f"Set slot[{msg.slot}].ai_type = {slot.ai_type}")

    def handle_start_game(self, _: pb.StartGame, timestamp, **__):
        logger.debug("Marking game as started")
        self.game_started = True
        self.game_started_time = float(timestamp)


class ReplayParsingError(Exception):
    pass
