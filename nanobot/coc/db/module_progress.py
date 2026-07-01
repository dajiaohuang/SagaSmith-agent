"""Scene/module progress tracking for CoC7."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from nanobot.ttrpg.db.base import Database


@dataclass
class SceneProgressInfo:
    id: str
    campaign_id: str
    scene_id: str
    current_room: str = ""
    explored_percent: int = 0
    state_json: dict = field(default_factory=dict)


class ModuleProgressService:
    """Track runtime progress within a module's scenes."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def set_scene(
        self,
        campaign_id: str,
        scene_id: str,
        current_room: str | None = None,
        explored_percent: int = 0,
        state_json: dict | None = None,
    ) -> SceneProgressInfo:
        """Set or update the current scene state."""
        return SceneProgressInfo(
            id=str(uuid4()),
            campaign_id=campaign_id,
            scene_id=scene_id,
            current_room=current_room or "",
            explored_percent=explored_percent,
            state_json=state_json or {},
        )

    def current(self, campaign_id: str) -> SceneProgressInfo | None:
        """Get the current scene state for a campaign."""
        return None
