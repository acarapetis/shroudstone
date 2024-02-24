"""Stormgate replay parsing tools"""
import gzip
import sys
from contextlib import contextmanager
from pathlib import Path
from pydantic import BaseModel
from typing import BinaryIO, Iterable, List, Optional, Union

from .stormgate_pb2 import ReplayChunk


@contextmanager
def decompress(replay: Union[Path, BinaryIO]):
    """Open a gzipped stormgate replay, skipping the 16-byte header."""
    if isinstance(replay, Path):
        replay = replay.open("rb")
    with replay:
        replay.seek(16)
        with gzip.GzipFile(fileobj=replay) as f2:
            yield f2


def read_varint(f) -> Optional[int]:
    """Read a base-7 varint from a binary stream"""
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


class MatchInfo(BaseModel):
    player_nicknames: List[str] = []
    map_name: Optional[str] = None


def get_match_info(replay: Union[Path, BinaryIO]) -> MatchInfo:
    """Parse what we can from a stormgate replay."""
    info = MatchInfo()
    for bytestring in split_replay(replay):
        chunk = ReplayChunk.FromString(bytestring)
        content = chunk.inner.content
        content_type = content.WhichOneof("contenttype")
        if content_type == "map":
            info.map_name = content.map.name
        if content_type == "player":
            info.player_nicknames.append(content.player.name.nickname)
        if len(info.player_nicknames) >= 2 and info.map_name is not None:
            break
    return info
