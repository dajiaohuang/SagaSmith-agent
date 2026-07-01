"""Runtime state ORM models — combat, saves, events, memories."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, Boolean,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from .common import TimestampMixin


class Combat(TimestampMixin):
    """A combat encounter — runtime state."""

    __tablename__ = "combats"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(200), default="")
    location = Column(String(200), default="")
    round_number = Column(Integer, default=1)
    current_turn = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    result = Column(Text, default="")
    environment_json = Column(JSON, default=dict)
    state_json = Column(JSON, default=dict)
    schema_version = Column(Integer, default=1)
    state_version = Column(Integer, default=1)


class CampaignSave(TimestampMixin):
    """An immutable snapshot of campaign state — a DAG node."""

    __tablename__ = "campaign_saves"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    slot = Column(Integer, nullable=False)  # human-facing slot number
    label = Column(String(200), default="")
    chapter = Column(String(200), default="")
    location = Column(String(200), default="")
    snapshot_json = Column(JSON, nullable=False)
    snapshot_format = Column(String(20), default="v2")
    snapshot_hash = Column(String(64), nullable=False)  # SHA-256
    recap = Column(JSON, nullable=True)
    created_by = Column(String(200), nullable=True)
    schema_version = Column(Integer, default=1)
    state_version = Column(Integer, default=1)
    parent_save_id = Column(String(36), ForeignKey("campaign_saves.id"), nullable=True)
    depth = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "slot", name="uq_save_campaign_slot"),
    )

    parent = relationship("CampaignSave", remote_side="CampaignSave.id", backref="children")


class CampaignTimelineHead(TimestampMixin):
    """Tracks the active save head for a campaign."""

    __tablename__ = "campaign_timeline_heads"

    campaign_id = Column(String(36), ForeignKey("campaigns.id"), primary_key=True)
    active_save_id = Column(String(36), ForeignKey("campaign_saves.id"), nullable=False)


class CampaignSaveAncestor(TimestampMixin):
    """Transitive closure for save DAG — enables fast lineage queries."""

    __tablename__ = "campaign_save_ancestors"

    id = Column(String(36), primary_key=True)
    descendant_save_id = Column(String(36), ForeignKey("campaign_saves.id"), nullable=False)
    ancestor_save_id = Column(String(36), ForeignKey("campaign_saves.id"), nullable=False)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    distance = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("descendant_save_id", "ancestor_save_id", name="uq_save_ancestor"),
    )


class CampaignEvent(TimestampMixin):
    """An event log entry for a campaign."""

    __tablename__ = "campaign_events"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    session_id = Column(String(36), nullable=True)
    event_type = Column(String(50), default="")  # combat / discovery / social / sanity / travel
    content = Column(Text, default="")
    actors = Column(JSON, default=list)
    visibility = Column(String(20), default="all")  # all / keeper / player
    importance = Column(Integer, default=1)  # 1-5
    metadata = Column(JSON, default=dict)


class CampaignMemory(TimestampMixin):
    """Stable identity of one campaign-scoped fact."""

    __tablename__ = "campaign_memories"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    kind = Column(String(50), default="")
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    fact_type = Column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "entity_type", "entity_id", "fact_type",
            name="uq_memory_fact",
        ),
    )


class CampaignMemoryRevision(TimestampMixin):
    """Immutable per-save value of a memory fact."""

    __tablename__ = "campaign_memory_revisions"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    memory_id = Column(String(36), ForeignKey("campaign_memories.id"), nullable=False)
    save_id = Column(String(36), ForeignKey("campaign_saves.id"), nullable=False)
    operation = Column(String(10), default="set")  # set / delete
    text = Column(Text, default="")
    priority = Column(String(20), default="medium")  # high / medium / low
    status = Column(String(20), default="candidate")  # candidate / stable / permanent

    __table_args__ = (
        UniqueConstraint("memory_id", "save_id", name="uq_memory_revision"),
    )
