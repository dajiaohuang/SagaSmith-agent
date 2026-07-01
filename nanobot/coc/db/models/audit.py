"""Audit trail ORM models — append-only."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, Boolean,
    ForeignKey, UniqueConstraint, event,
)
from .common import TimestampMixin


class DiceRoll(TimestampMixin):
    """An audited dice roll — append-only."""

    __tablename__ = "dice_rolls"

    id = Column(String(36), primary_key=True)
    request_id = Column(String(36), nullable=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=True)
    formula = Column(String(200), nullable=False)
    result = Column(JSON, nullable=False)
    detail_json = Column(JSON, default=dict)
    context = Column(JSON, default=dict)
    tool_name = Column(String(100), default="")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ToolAudit(TimestampMixin):
    """An audited tool invocation — append-only."""

    __tablename__ = "tool_audits"

    id = Column(String(36), primary_key=True)
    request_id = Column(String(36), nullable=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True)
    reverts_audit_id = Column(String(36), ForeignKey("tool_audits.id"), nullable=True)
    session_id = Column(String(36), nullable=True)
    actor_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=False)
    engine_function = Column(String(200), default="")
    arguments_json = Column(JSON, default=dict)
    result_json = Column(JSON, default=dict)
    before_state_json = Column(JSON, nullable=True)
    after_state_json = Column(JSON, nullable=True)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)
    state_version = Column(Integer, nullable=True)


class StateRevision(TimestampMixin):
    """A revision of an aggregate state — append-only."""

    __tablename__ = "state_revisions"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    tool_audit_id = Column(String(36), ForeignKey("tool_audits.id"), nullable=True)
    actor_id = Column(String(100), nullable=True)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_key = Column(String(100), nullable=False)
    engine_function = Column(String(200), default="")
    state_version = Column(Integer, nullable=False)
    before_state_json = Column(JSON, nullable=True)
    after_state_json = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "aggregate_type", "aggregate_key", "state_version",
            name="uq_state_revision",
        ),
    )


# -- Append-only enforcement via SQLAlchemy events --


def _prevent_update(mapper, connection, target):
    raise PermissionError(
        f"UPDATE is not permitted on append-only table: {target.__tablename__}"
    )


def _prevent_delete(mapper, connection, target):
    raise PermissionError(
        f"DELETE is not permitted on append-only table: {target.__tablename__}"
    )


for _model in (DiceRoll, ToolAudit, StateRevision):
    event.listen(_model, "before_update", _prevent_update)
    event.listen(_model, "before_delete", _prevent_delete)
