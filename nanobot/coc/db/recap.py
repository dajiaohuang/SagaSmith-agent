"""Narrative recap generation for CoC7 snapshots."""

from __future__ import annotations

from typing import Any


class RecapGenerator:
    """Generate narrative recaps by comparing snapshot states."""

    def __init__(self, provider: Any = None, model: str = "") -> None:
        self.provider = provider
        self.model = model

    async def generate(
        self,
        campaign_id: str,
        previous_save: Any | None = None,
        current_payload: dict | None = None,
    ) -> dict:
        """Generate a narrative recap."""
        return {
            "version": 1,
            "baseline": previous_save is None,
            "from_save_id": None,
            "to_save_id": None,
            "generated_at": "",
            "language": "zh-CN",
            "summary": "存档完成。",
            "plot_progress": [],
            "new_characters": [],
            "new_locations": [],
            "triggered_events": [],
            "future_impact": [],
            "player_choices": [],
            "memory_candidates": [],
            "source": {"mode": "placeholder"},
        }
