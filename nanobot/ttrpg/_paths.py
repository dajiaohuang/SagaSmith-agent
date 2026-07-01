"""Platform-neutral runtime paths for TTRPG subsystems."""

import os
from pathlib import Path


def get_runtime_subdir(*parts: str) -> Path:
    """Return a platform-appropriate runtime data directory under ~/.sagasmith."""
    base = Path.home() / ".sagasmith"
    target = base.joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return target
