"""Shared base classes and mixins for all ORM models."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, func


class TimestampMixin:
    """Mixin adding created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
