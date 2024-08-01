from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
Disconnect: LeaveReason
Leave: LeaveReason
Surrender: LeaveReason
Unknown: LeaveReason

class AssignPlayerSlot(_message.Message):
    __slots__ = ["nickname", "slot", "uuid"]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    nickname: str
    slot: int
    uuid: UUID
    def __init__(self, uuid: _Optional[_Union[UUID, _Mapping]] = ..., slot: _Optional[int] = ..., nickname: _Optional[str] = ...) -> None: ...

class ClientConnected(_message.Message):
    __slots__ = ["client_id", "uuid"]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    client_id: int
    uuid: UUID
    def __init__(self, client_id: _Optional[int] = ..., uuid: _Optional[_Union[UUID, _Mapping]] = ...) -> None: ...

class ClientDisconnected(_message.Message):
    __slots__ = ["client_id", "player_uuid", "reason"]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    PLAYER_UUID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    client_id: int
    player_uuid: UUID
    reason: LeaveReason
    def __init__(self, client_id: _Optional[int] = ..., reason: _Optional[_Union[LeaveReason, str]] = ..., player_uuid: _Optional[_Union[UUID, _Mapping]] = ...) -> None: ...

class LobbyChangeSlot(_message.Message):
    __slots__ = ["choice"]
    class SlotChoice(_message.Message):
        __slots__ = ["specific_slot"]
        class SpecificSlot(_message.Message):
            __slots__ = ["slot"]
            SLOT_FIELD_NUMBER: _ClassVar[int]
            slot: int
            def __init__(self, slot: _Optional[int] = ...) -> None: ...
        SPECIFIC_SLOT_FIELD_NUMBER: _ClassVar[int]
        specific_slot: LobbyChangeSlot.SlotChoice.SpecificSlot
        def __init__(self, specific_slot: _Optional[_Union[LobbyChangeSlot.SlotChoice.SpecificSlot, _Mapping]] = ...) -> None: ...
    CHOICE_FIELD_NUMBER: _ClassVar[int]
    choice: LobbyChangeSlot.SlotChoice
    def __init__(self, choice: _Optional[_Union[LobbyChangeSlot.SlotChoice, _Mapping]] = ...) -> None: ...

class LobbySetVariable(_message.Message):
    __slots__ = ["slot", "value", "variable_id"]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_ID_FIELD_NUMBER: _ClassVar[int]
    slot: int
    value: int
    variable_id: int
    def __init__(self, slot: _Optional[int] = ..., variable_id: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class Map(_message.Message):
    __slots__ = ["folder", "name", "seed"]
    FOLDER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    folder: str
    name: str
    seed: int
    def __init__(self, folder: _Optional[str] = ..., name: _Optional[str] = ..., seed: _Optional[int] = ...) -> None: ...

class Player(_message.Message):
    __slots__ = ["name", "uuid"]
    class PlayerName(_message.Message):
        __slots__ = ["discriminator", "nickname"]
        DISCRIMINATOR_FIELD_NUMBER: _ClassVar[int]
        NICKNAME_FIELD_NUMBER: _ClassVar[int]
        discriminator: str
        nickname: str
        def __init__(self, nickname: _Optional[str] = ..., discriminator: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    name: Player.PlayerName
    uuid: UUID
    def __init__(self, uuid: _Optional[_Union[UUID, _Mapping]] = ..., name: _Optional[_Union[Player.PlayerName, _Mapping]] = ...) -> None: ...

class PlayerLeftGame(_message.Message):
    __slots__ = ["player_uuid", "reason"]
    PLAYER_UUID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    player_uuid: UUID
    reason: LeaveReason
    def __init__(self, player_uuid: _Optional[_Union[UUID, _Mapping]] = ..., reason: _Optional[_Union[LeaveReason, str]] = ...) -> None: ...

class ReplayChunk(_message.Message):
    __slots__ = ["client_id", "inner", "timestamp"]
    class Wrapper(_message.Message):
        __slots__ = ["content"]
        class ReplayContent(_message.Message):
            __slots__ = ["assign_player_slot", "change_slot", "client_connected", "client_disconnected", "map", "player", "player_left_game", "set_variable", "start_game"]
            ASSIGN_PLAYER_SLOT_FIELD_NUMBER: _ClassVar[int]
            CHANGE_SLOT_FIELD_NUMBER: _ClassVar[int]
            CLIENT_CONNECTED_FIELD_NUMBER: _ClassVar[int]
            CLIENT_DISCONNECTED_FIELD_NUMBER: _ClassVar[int]
            MAP_FIELD_NUMBER: _ClassVar[int]
            PLAYER_FIELD_NUMBER: _ClassVar[int]
            PLAYER_LEFT_GAME_FIELD_NUMBER: _ClassVar[int]
            SET_VARIABLE_FIELD_NUMBER: _ClassVar[int]
            START_GAME_FIELD_NUMBER: _ClassVar[int]
            assign_player_slot: AssignPlayerSlot
            change_slot: LobbyChangeSlot
            client_connected: ClientConnected
            client_disconnected: ClientDisconnected
            map: Map
            player: Player
            player_left_game: PlayerLeftGame
            set_variable: LobbySetVariable
            start_game: StartGame
            def __init__(self, map: _Optional[_Union[Map, _Mapping]] = ..., client_connected: _Optional[_Union[ClientConnected, _Mapping]] = ..., player: _Optional[_Union[Player, _Mapping]] = ..., change_slot: _Optional[_Union[LobbyChangeSlot, _Mapping]] = ..., set_variable: _Optional[_Union[LobbySetVariable, _Mapping]] = ..., start_game: _Optional[_Union[StartGame, _Mapping]] = ..., player_left_game: _Optional[_Union[PlayerLeftGame, _Mapping]] = ..., client_disconnected: _Optional[_Union[ClientDisconnected, _Mapping]] = ..., assign_player_slot: _Optional[_Union[AssignPlayerSlot, _Mapping]] = ...) -> None: ...
        CONTENT_FIELD_NUMBER: _ClassVar[int]
        content: ReplayChunk.Wrapper.ReplayContent
        def __init__(self, content: _Optional[_Union[ReplayChunk.Wrapper.ReplayContent, _Mapping]] = ...) -> None: ...
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    INNER_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    client_id: int
    inner: ReplayChunk.Wrapper
    timestamp: int
    def __init__(self, timestamp: _Optional[int] = ..., client_id: _Optional[int] = ..., inner: _Optional[_Union[ReplayChunk.Wrapper, _Mapping]] = ...) -> None: ...

class StartGame(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class UUID(_message.Message):
    __slots__ = ["part1", "part2"]
    PART1_FIELD_NUMBER: _ClassVar[int]
    PART2_FIELD_NUMBER: _ClassVar[int]
    part1: int
    part2: int
    def __init__(self, part1: _Optional[int] = ..., part2: _Optional[int] = ...) -> None: ...

class LeaveReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
