"""Feature-detected Blender API compatibility helpers."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def iter_action_fcurves(action: Any) -> Iterator[Any]:
    """Yield legacy or layered Action FCurves without a version-number branch."""
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        yield from legacy
        return
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                yield from getattr(channelbag, "fcurves", ())
