"""Stormgate replay parsing tools"""

from __future__ import annotations

import gzip
import logging
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from . import stormgate_pb2 as pb

logger = logging.getLogger(__name__)


# My empirical testing found that the timestamps in replays seem to be in units of ~0.976ms.
# This is very close to 1/1024 of a second, so we'll assume that this is the exact value.
REPLAY_TIMESTAMP_UNIT = 1 / 1024

FRIGATE = 55366


def decompress(replay: Union[Path, BinaryIO]) -> BytesIO:
    """Decompress a gzipped stormgate replay, skipping the 16-byte header."""
    if isinstance(replay, Path):
        replay = replay.open("rb")
    with replay:
        replay.seek(16)
        return BytesIO(gzip.decompress(replay.read()))


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


def read_varint(f: BinaryIO) -> Optional[int]:
    """Read a base-7 varint from a binary stream, or return None if the stream is at EOF."""
    # This recursive implementation would be slow for large varints; but since almost
    # all replay chunks are <128 bytes, we very rarely actually recurse; and on averaget
    # his ends up signficantly faster than an iterative implementation.
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
    f = decompress(replay)
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
            if client.nickname is None:
                raise ReplayParsingError(
                    f"No nickname found for client {client.client_id} = {client.uuid}?"
                )
            info.players.append(
                p := Player(
                    nickname=client.nickname,
                    nickname_discriminator=client.discriminator,
                    uuid=client.uuid,
                    is_ai=False,
                    faction=slot.faction.name,
                )
            )
            if (
                state.game_started_time is not None
                and client.left_game_time is not None
            ):
                p.disconnect_time = (
                    client.left_game_time - state.game_started_time
                ) * REPLAY_TIMESTAMP_UNIT
            p.leave_reason = client.left_game_reason.name
    for client in state.clients.values():
        if client.slot_number != 255:
            raise ReplayParsingError("Player not in a slot but slot_number != 255?")
        if client.nickname is None:
            raise ReplayParsingError(
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


# Unfortunately, to correctly determine who's in player slots and who's in spectator
# slots we need to know how many players the map has; and this metadata is not included
# in the replay. (We have MatchType info now, but this doesn't help for Custom games.)
# For now, we just hardcode the known maps.
player_slot_count: Dict[str, int] = {
    "Boneyard": 2,
    "BrokenCrown": 2,
    "IsleOfDread": 2,
    "LostHope": 2,
    "SecludedGroveV2": 2,
    "TitansCausewayV2": 2,
    "JaggedMaw": 2,
    "CrookedCanyon": 3,
    "InfestedCrater": 3,
    "RitualWoods": 3,
    "TheAbyssalGates": 3,
    "TurfWar": 3,
    "WreckHavoc": 3,
    "Boneyard2v2": 4,
    "DustDevil2v2": 4,
    "Evergreen2v2": 4,
}


class SlotType(IntEnum):
    Closed = 0
    Human = 1
    Ai = 2


class Faction(IntEnum):
    Vanguard = 0
    Infernals = 1
    Celestial = 2
    Blockade = 101
    Amara = 102
    Maloc = 201
    Warz = 202
    Auralanna = 301


class AIType(IntEnum):
    PeacefulBot = 0
    MurderBotJr = 1
    MurderBotSr = 2


@dataclass()
class Slot:
    type: SlotType = SlotType.Human
    faction: Faction = Faction(0)
    ai_type: Optional[AIType] = None
    client_id: Optional[int] = None


# The python protobuf bindings don't use standard python enums - they just return ints.
# I want nice type hints so I'm just going to maintain this manually.
class LeftGameReason(IntEnum):
    Unknown = 0
    Surrender = 1
    Leave = 2
    Disconnect = 3


class MatchType(IntEnum):
    Unknown = 0
    Custom = 1
    Ranked1v1 = 2
    Coop3ve = 3


@dataclass()
class Client:
    uuid: UUID
    client_id: int
    nickname: Optional[str] = None
    discriminator: Optional[str] = None
    slot_number: Optional[int] = None  # 255 means spectator
    left_game_time: Optional[float] = None
    left_game_reason: LeftGameReason = LeftGameReason.Unknown


@dataclass()
class SlotAssignment:
    slot_number: int
    nickname: str


def parse_uuid(uuid: pb.UUID) -> UUID:
    return UUID(bytes=struct.pack(">QQ", uuid.part1, uuid.part2))


@dataclass()
class GameState:
    """Stormgate match state machine - reads commands from replay and updates state"""

    map_name: Optional[str] = None
    match_type: MatchType = MatchType.Unknown
    slots: Dict[int, Slot] = field(default_factory=dict)
    clients: Dict[int, Client] = field(default_factory=dict)
    slot_assignments: Dict[UUID, SlotAssignment] = field(default_factory=dict)
    game_started: bool = False
    game_started_time: Optional[float] = None

    @classmethod
    def at_end_of(cls, replay: Union[Path, BinaryIO]) -> GameState:
        """Simulate an entire replay and return the end state."""
        self = cls()
        # Using split_replay adds a significant overhead to the runtime of this
        # function; so I've inlined this loop instead.
        f = decompress(replay)
        while length := read_varint(f):
            self.process(pb.ReplayChunk.FromString(f.read(length)))
        return self

    def process(self, chunk: pb.ReplayChunk):
        """Update the state using a single replay chunk/command."""
        content = chunk.inner.content
        content_type = content.WhichOneof("content_type")
        if not content_type:
            return
        msg = getattr(content, content_type)
        client_id = chunk.client_id
        timestamp = chunk.timestamp

        if isinstance(msg, pb.MapDetails):
            self.map_name = msg.map_name
            self.match_type = MatchType(msg.match_type)

            if self.match_type == MatchType.Ranked1v1:
                slot_count = 2
            elif self.match_type == MatchType.Coop3ve:
                slot_count = 3
            else:
                try:
                    # Fall back to old system
                    slot_count = player_slot_count[msg.map_name]
                except KeyError:
                    raise ReplayParsingError(
                        f"Unknown map {msg.map_name} - cannot correctly determine player slots!"
                    )

            logger.debug(f"MatchType: {self.match_type}")

            logger.debug(f"Setting up {slot_count} slots for map {self.map_name}")
            for i in range(1, slot_count + 1):
                self.slots[i] = Slot()

        elif isinstance(msg, pb.AssignPlayerSlot):
            self.slot_assignments[parse_uuid(msg.uuid)] = SlotAssignment(
                slot_number=msg.slot, nickname=msg.nickname
            )
            logger.debug(f"Assigning slot {msg.slot} to {msg.uuid}")

        elif isinstance(msg, pb.Player):
            self.clients[client_id] = client = Client(
                client_id=client_id,
                uuid=parse_uuid(msg.uuid),
                nickname=msg.name.nickname,
                discriminator=msg.name.discriminator,
            )
            logger.debug(
                f"Setting up player {client_id}: {client.nickname} {client.uuid}"
            )
            # If we're in a matchmaking game, the server has pre-assigned a slot for the player:
            if (assignment := self.slot_assignments.get(client.uuid)) is not None:
                client.slot_number = assignment.slot_number
                self.slots[assignment.slot_number].client_id = client_id
                logger.debug(
                    f"Putting player {client_id} in pre-assigned slot {client.slot_number}"
                )

        elif isinstance(msg, pb.ClientConnected):
            if not msg.HasField("uuid"):
                # We should have already filled in the player details in handle_player,
                # don't worry about it
                return
            self.clients[msg.client_id] = client = Client(
                client_id=msg.client_id,
                uuid=parse_uuid(msg.uuid),
            )
            logger.debug(f"Setting up player {client.client_id}: {client.uuid}")
            if (assignment := self.slot_assignments.get(client.uuid)) is not None:
                client.slot_number = assignment.slot_number
                if client.nickname is not None:
                    assert client.nickname == assignment.nickname
                else:
                    client.nickname = assignment.nickname
                self.slots[assignment.slot_number].client_id = client.client_id
                logger.debug(
                    f"Putting player {client.client_id} in pre-assigned slot {client.slot_number}"
                )

        elif isinstance(msg, pb.PlayerLeftGame):
            if self.game_started:
                self.clients[client_id].left_game_time = timestamp
                self.clients[client_id].left_game_reason = LeftGameReason(msg.reason)
            else:
                client = self.clients.pop(client_id, None)
                # In aborted ladder games, we sometimes get a left game before the player joined message
                suffix = (
                    f": {client.nickname} {client.uuid}" if client is not None else ""
                )
                logger.debug(f"Removing player {client_id}: {suffix}")
                for slot in self.slots.values():
                    if slot.client_id == client_id:
                        slot.client_id = None

        elif isinstance(msg, pb.ClientDisconnected):
            if self.game_started:
                client = self.clients[msg.client_id]
                if client.left_game_time is None:
                    # Server telling us client disconnected without leaving cleanly
                    assert client.uuid == parse_uuid(msg.player_uuid)
                    client.left_game_time = timestamp
                    client.left_game_reason = LeftGameReason(msg.reason)

        elif isinstance(msg, pb.LobbyChangeSlot):
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
                    if slot.type == SlotType.Human and slot.client_id is None:
                        break
                else:
                    # No open slots, become spectator
                    slot_number = 255
            client.slot_number = slot_number
            if slot_number != 255:
                slot = self.slots[slot_number]
                if slot.type != SlotType.Human:
                    raise ReplayParsingError("Client assigned to non-human slot?")
                if slot.client_id is not None:
                    raise ReplayParsingError(
                        "Client assigned to already occupied slot?"
                    )
                slot.client_id = client_id
                logger.debug(f"Putting player {client_id} in slot {slot_number}")

        elif isinstance(msg, pb.LobbySetVariable):
            slot = self.slots[msg.slot]
            key = msg.variable_id
            value = msg.value
            if key == 374945738:
                slot.type = SlotType(value)
                logger.debug(f"Set slot[{msg.slot}].type = {slot.type}")
                if slot.type == SlotType.Ai:
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

        elif isinstance(msg, pb.StartGame):
            logger.debug("Marking game as started")
            self.game_started = True
            self.game_started_time = float(timestamp)


class ReplayParsingError(Exception):
    pass
