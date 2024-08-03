from typing import ClassVar, Dict, Optional
from uuid import UUID


class SlotType:
    closed: ClassVar["SlotType"]
    human: ClassVar["SlotType"]
    ai: ClassVar["SlotType"]


class Faction:
    vanguard: ClassVar["Faction"]
    infernals: ClassVar["Faction"]
    celestial: ClassVar["Faction"]
    blockade: ClassVar["Faction"]
    amara: ClassVar["Faction"]
    maloc: ClassVar["Faction"]
    warz: ClassVar["Faction"]
    auralanna: ClassVar["Faction"]


class AIType:
    PeacefulBot: ClassVar["AIType"]
    MurderBotJr: ClassVar["AIType"]
    MurderBotSr: ClassVar["AIType"]


class Slot:
    type: SlotType
    faction: Faction
    ai_type: Optional[AIType]
    client_id: Optional[int]


class LeaveReason:
    Unknown: ClassVar["LeaveReason"]
    Surrender: ClassVar["LeaveReason"]
    Leave: ClassVar["LeaveReason"]
    Disconnect: ClassVar["LeaveReason"]


# class MatchType
#     unknown = 0
#     custom = 1
#     ranked1v1 = 2
#     coop3ve = 3


class Client:
    uuid: UUID
    client_id: int
    nickname: Optional[str]
    discriminator: Optional[str]
    slot_number: Optional[int]
    left_game_time: Optional[float]
    left_game_reason: LeaveReason


class SlotAssignment:
    slot_number: int
    nickname: str


class GameState:
    map_name: Optional[str]
    #match_type: MatchType
    slots: Dict[int, Slot]
    clients: Dict[int, Client]
    slot_assignments: Dict[UUID, SlotAssignment]
    game_started: bool
    game_started_time: Optional[float]


def simulate_replay_file(path: str) -> GameState: ...
