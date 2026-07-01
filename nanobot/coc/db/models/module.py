"""Module / scenario content ORM models."""

from sqlalchemy import (
    Column, String, Text, Integer, JSON, Boolean, ForeignKey, UniqueConstraint,
)
from .common import TimestampMixin


class ModuleSource(TimestampMixin):
    """An imported scenario/module source."""

    __tablename__ = "module_sources"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(200), nullable=False)
    source_path = Column(String(500), default="")
    checksum = Column(String(64), default="")
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("campaign_id", "name", name="uq_module_name"),
    )


class ModuleChapter(TimestampMixin):
    """A chapter within a module."""

    __tablename__ = "module_chapters"

    id = Column(String(36), primary_key=True)
    module_id = Column(String(36), ForeignKey("module_sources.id"), nullable=False)
    chapter_key = Column(String(100), nullable=False)
    title = Column(String(300), default="")
    source_path = Column(String(500), default="")
    content = Column(Text, default="")
    order_index = Column(Integer, default=0)
    status = Column(String(20), default="locked")  # locked / unlocked / active
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("module_id", "chapter_key", name="uq_chapter_key"),
    )


class SceneIndex(TimestampMixin):
    """A scene within a chapter — line-number indexed."""

    __tablename__ = "scene_indexes"

    id = Column(String(36), primary_key=True)
    chapter_id = Column(String(36), ForeignKey("module_chapters.id"), nullable=False)
    scene_key = Column(String(100), nullable=False)
    title = Column(String(300), default="")
    start_line = Column(Integer, default=0)
    end_line = Column(Integer, default=0)
    headings = Column(JSON, default=list)
    keywords = Column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint("chapter_id", "scene_key", name="uq_scene_key"),
    )


class ModuleChunk(TimestampMixin):
    """A chunk of module text with optional embedding."""

    __tablename__ = "module_chunks"

    id = Column(String(36), primary_key=True)
    module_id = Column(String(36), ForeignKey("module_sources.id"), nullable=False)
    chapter_id = Column(String(36), ForeignKey("module_chapters.id"), nullable=True)
    scene_id = Column(String(36), ForeignKey("scene_indexes.id"), nullable=True)
    embedding_model_id = Column(String(36), ForeignKey("embedding_models.id"), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    heading = Column(String(300), default="")
    breadcrumb = Column(Text, default="")
    start_line = Column(Integer, default=0)
    end_line = Column(Integer, default=0)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    chunk_type = Column(
        String(20), default="narrative",
    )  # narrative / room / statblock / table / read_aloud / list / toc
    token_count = Column(Integer, default=0)
    content_hash = Column(String(64), default="")
    chunk_text = Column(Text, default="")
    search_text = Column(Text, default="")
    embedding_json = Column(JSON, nullable=True)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("chapter_id", "chunk_index", name="uq_module_chunk"),
    )


class SceneState(TimestampMixin):
    """Runtime progress within a scene."""

    __tablename__ = "scene_states"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    scene_id = Column(String(36), ForeignKey("scene_indexes.id"), nullable=False)
    current_room = Column(String(200), default="")
    explored_percent = Column(Integer, default=0)
    state_json = Column(JSON, default=dict)
    schema_version = Column(Integer, default=1)
    state_version = Column(Integer, default=1)

    __table_args__ = (
        UniqueConstraint("campaign_id", "scene_id", name="uq_scene_state"),
    )
