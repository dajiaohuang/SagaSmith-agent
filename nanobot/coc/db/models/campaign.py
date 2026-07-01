"""Campaign ORM models."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from .common import TimestampMixin


class Campaign(TimestampMixin):
    """A CoC7 campaign — the top-level organizational unit."""

    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    system_version = Column(String(100), default="Call of Cthulhu 7e")
    module_name = Column(String(200), nullable=True)
    engine_source = Column(String(200), nullable=True)
    engine_version = Column(String(50), nullable=True)
    status = Column(String(20), default="active")  # active / archived
    description = Column(Text, default="")
    config = Column(JSON, default=dict)
    schema_version = Column(Integer, default=1)


class WorldState(TimestampMixin):
    """Mutable world state for a campaign — one-to-one with Campaign."""

    __tablename__ = "world_states"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), unique=True, nullable=False)
    state_json = Column(
        JSON,
        default=lambda: {
            "faction_relations": {},
            "discovered_locations": [],
            "quest_progress": {},
            "key_npc_status": {},
            "current_chapter": "",
            "current_scene": "",
            "day_in_game": 1,
        },
    )
    schema_version = Column(Integer, default=1)
    state_version = Column(Integer, default=1)

    campaign = relationship("Campaign", backref="world_state")


class Party(TimestampMixin):
    """Investigator party — one-to-one with Campaign."""

    __tablename__ = "parties"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), unique=True, nullable=False)
    name = Column(String(200), default="调查员团队")
    location = Column(String(200), default="")
    shared_gold = Column(Integer, default=0)
    state_json = Column(JSON, default=dict)
    schema_version = Column(Integer, default=1)
    state_version = Column(Integer, default=1)

    campaign = relationship("Campaign", backref="party")


class PlotSummary(TimestampMixin):
    """Plot summary for a campaign scope."""

    __tablename__ = "plot_summaries"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    scope = Column(String(50), default="campaign")  # campaign / chapter / scene
    scope_id = Column(String(36), nullable=True)
    summary = Column(Text, default="")
    open_threads = Column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint("campaign_id", "scope", "scope_id", name="uq_plot_campaign_scope"),
    )
