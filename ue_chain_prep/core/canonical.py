"""Deterministic binary encoding and hashing for immutable plans and graphs."""

from __future__ import annotations

import dataclasses
import hashlib
import struct
from collections.abc import Mapping
from enum import Enum


def encode(value) -> bytes:
    if value is None:
        return b"n"
    if isinstance(value, bool):
        return b"b" + bytes((1 if value else 0,))
    if isinstance(value, int):
        return b"i" + struct.pack("<q", value)
    if isinstance(value, float):
        return b"f" + struct.pack("<d", value)
    if isinstance(value, str):
        payload = value.encode("utf-8")
        return b"s" + struct.pack("<I", len(payload)) + payload
    if isinstance(value, Enum):
        return encode(value.value)
    if dataclasses.is_dataclass(value):
        return encode({field.name: getattr(value, field.name) for field in dataclasses.fields(value)})
    if isinstance(value, Mapping):
        items = sorted(value.items(), key=lambda item: str(item[0]))
        return b"m" + struct.pack("<I", len(items)) + b"".join(encode(key) + encode(item) for key, item in items)
    if isinstance(value, (tuple, list)):
        return b"q" + struct.pack("<I", len(value)) + b"".join(encode(item) for item in value)
    raise TypeError(f"unsupported canonical type: {type(value)!r}")


def sha256(value) -> str:
    return hashlib.sha256(encode(value)).hexdigest()
