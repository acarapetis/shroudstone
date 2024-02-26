from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Map(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class UUID(_message.Message):
    __slots__ = ("part1", "part2")
    PART1_FIELD_NUMBER: _ClassVar[int]
    PART2_FIELD_NUMBER: _ClassVar[int]
    part1: int
    part2: int
    def __init__(self, part1: _Optional[int] = ..., part2: _Optional[int] = ...) -> None: ...

class Player(_message.Message):
    __slots__ = ("uuid", "name")
    class PlayerName(_message.Message):
        __slots__ = ("nickname", "discriminator")
        NICKNAME_FIELD_NUMBER: _ClassVar[int]
        DISCRIMINATOR_FIELD_NUMBER: _ClassVar[int]
        nickname: str
        discriminator: str
        def __init__(self, nickname: _Optional[str] = ..., discriminator: _Optional[str] = ...) -> None: ...
    UUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    uuid: UUID
    name: Player.PlayerName
    def __init__(self, uuid: _Optional[_Union[UUID, _Mapping]] = ..., name: _Optional[_Union[Player.PlayerName, _Mapping]] = ...) -> None: ...

class ReplayChunk(_message.Message):
    __slots__ = ("timestamp", "inner")
    class Wrapper(_message.Message):
        __slots__ = ("content",)
        class ReplayContent(_message.Message):
            __slots__ = ("map", "player")
            MAP_FIELD_NUMBER: _ClassVar[int]
            PLAYER_FIELD_NUMBER: _ClassVar[int]
            map: Map
            player: Player
            def __init__(self, map: _Optional[_Union[Map, _Mapping]] = ..., player: _Optional[_Union[Player, _Mapping]] = ...) -> None: ...
        CONTENT_FIELD_NUMBER: _ClassVar[int]
        content: ReplayChunk.Wrapper.ReplayContent
        def __init__(self, content: _Optional[_Union[ReplayChunk.Wrapper.ReplayContent, _Mapping]] = ...) -> None: ...
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    INNER_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    inner: ReplayChunk.Wrapper
    def __init__(self, timestamp: _Optional[int] = ..., inner: _Optional[_Union[ReplayChunk.Wrapper, _Mapping]] = ...) -> None: ...
