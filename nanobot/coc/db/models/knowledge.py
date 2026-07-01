"""Knowledge / rules corpus ORM models."""

from sqlalchemy import (
    Column, String, Text, Integer, JSON, Boolean, Float,
    ForeignKey, UniqueConstraint,
)
from .common import TimestampMixin


class RuleSet(TimestampMixin):
    """A game system rule set — acts as the namespace root."""

    __tablename__ = "rule_sets"

    id = Column(String(36), primary_key=True)
    game_system = Column(String(50), nullable=False)  # "CoC7"
    edition = Column(String(50), nullable=False)       # "7e"
    release = Column(String(50), default="")           # "1.0"
    locale = Column(String(10), default="en")          # "en" / "zh-CN"
    status = Column(String(20), default="active")
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("game_system", "edition", "release", "locale", name="uq_rule_set"),
    )


class RulePublication(TimestampMixin):
    """A rule publication (book) within a rule set."""

    __tablename__ = "rule_publications"

    id = Column(String(36), primary_key=True)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=False)
    parent_publication_id = Column(String(36), ForeignKey("rule_publications.id"), nullable=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False)
    publication_type = Column(String(20), default="core")  # core / supplement / errata
    priority = Column(Integer, default=0)
    license = Column(String(100), default="")
    effective_date = Column(String(20), default="")
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("rule_set_id", "slug", name="uq_publication_slug"),
    )


class EmbeddingModel(TimestampMixin):
    """Embedding model configuration for vector search."""

    __tablename__ = "embedding_models"

    id = Column(String(36), primary_key=True)
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    dimensions = Column(Integer, nullable=False)
    distance_metric = Column(String(20), default="cosine")
    content_template_version = Column(String(10), default="v2")
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("provider", "model_name", "dimensions", name="uq_embedding_model"),
    )


class RuleSource(TimestampMixin):
    """A source file or document imported into the rule corpus."""

    __tablename__ = "rule_sources"

    id = Column(String(36), primary_key=True)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=False)
    publication_id = Column(String(36), ForeignKey("rule_publications.id"), nullable=True)
    name = Column(String(200), nullable=False)
    source_path = Column(String(500), nullable=False)
    source_type = Column(String(20), default="markdown")  # markdown / pdf / html
    system_version = Column(String(50), default="")
    locale = Column(String(10), default="en")
    checksum = Column(String(64), default="")
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("source_path", name="uq_source_path"),
    )


class RuleSection(TimestampMixin):
    """A heading-delimited section within a rule source."""

    __tablename__ = "rule_sections"

    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey("rule_sources.id"), nullable=False)
    publication_id = Column(String(36), ForeignKey("rule_publications.id"), nullable=True)
    parent_id = Column(String(36), ForeignKey("rule_sections.id"), nullable=True)
    section_type = Column(String(20), default="section")
    title = Column(String(300), nullable=False)
    slug = Column(String(100), default="")
    path = Column(String(500), nullable=False)
    heading_path = Column(JSON, default=list)
    depth = Column(Integer, default=0)
    order_index = Column(Integer, default=0)
    start_line = Column(Integer, default=0)
    end_line = Column(Integer, default=0)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("source_id", "path", name="uq_section_path"),
    )


class RuleChunk(TimestampMixin):
    """A chunk of rule text with optional embedding."""

    __tablename__ = "rule_chunks"

    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey("rule_sources.id"), nullable=False)
    section_id = Column(String(36), ForeignKey("rule_sections.id"), nullable=True)
    embedding_model_id = Column(String(36), ForeignKey("embedding_models.id"), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    heading = Column(String(300), default="")
    breadcrumb = Column(Text, default="")
    start_line = Column(Integer, default=0)
    end_line = Column(Integer, default=0)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    content_hash = Column(String(64), default="")
    chunk_text = Column(Text, default="")
    search_text = Column(Text, default="")
    embedding_json = Column(JSON, nullable=True)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index", name="uq_chunk_index"),
    )


class CompendiumEntry(TimestampMixin):
    """A compendium entry — spell, skill, item, monster, etc."""

    __tablename__ = "compendium_entries"

    id = Column(String(36), primary_key=True)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=False)
    publication_id = Column(String(36), ForeignKey("rule_publications.id"), nullable=True)
    section_id = Column(String(36), ForeignKey("rule_sections.id"), nullable=True)
    supersedes_entry_id = Column(String(36), ForeignKey("compendium_entries.id"), nullable=True)
    entry_type = Column(
        String(20), nullable=False,
    )  # skill / occupation / spell / tome / talent / condition / item / mythos_entity
    name = Column(String(200), nullable=False)
    aliases = Column(JSON, default=list)
    data_json = Column(JSON, default=dict)
    source = Column(String(200), default="")
    system_version = Column(String(50), default="")

    __table_args__ = (
        UniqueConstraint("entry_type", "name", "system_version", name="uq_compendium_entry"),
    )


class CampaignRuleProfile(TimestampMixin):
    """Links a campaign to its pinned rule set."""

    __tablename__ = "campaign_rule_profiles"

    id = Column(String(36), primary_key=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), unique=True, nullable=False)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=False)
    locale = Column(String(10), default="en")


class CampaignRulePublication(TimestampMixin):
    """Enabled publications for a campaign's rule profile."""

    __tablename__ = "campaign_rule_publications"

    id = Column(String(36), primary_key=True)
    profile_id = Column(String(36), ForeignKey("campaign_rule_profiles.id"), nullable=False)
    publication_id = Column(String(36), ForeignKey("rule_publications.id"), nullable=False)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("profile_id", "publication_id", name="uq_profile_publication"),
    )
