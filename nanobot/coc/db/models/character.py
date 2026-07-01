"""Character ORM model — COC Investigator / NPC / Creature."""

from sqlalchemy import (
    Column, String, Text, Integer, JSON, ForeignKey, UniqueConstraint,
)
from .common import TimestampMixin


class Character(TimestampMixin):
    """
    COC character — investigator, NPC, or creature.

    Mirrors DND's Character model but replaces DND-specific fields
    (class_name, level, race, background, alignment, armor_class)
    with COC-specific fields (occupation, archetype, age, etc.).

    Full COC sheet data lives in `sheet_json`.
    """

    __tablename__ = "characters"

    id = Column(String(36), primary_key=True)
    character_type = Column(String(20), default="investigator")  # investigator / npc / creature / container
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True)
    party_id = Column(String(36), ForeignKey("parties.id"), nullable=True)

    # Identity
    name = Column(String(200), nullable=False)
    player_name = Column(String(200), nullable=True)

    # COC-specific identity fields
    occupation = Column(String(200), default="")
    archetype = Column(String(200), default="")
    age = Column(String(20), default="")
    sex = Column(String(20), default="")
    residence = Column(String(200), default="")
    birthplace = Column(String(200), default="")
    organization = Column(String(200), default="")

    # Full COC sheet as JSON (flexible schema for CoC 7e)
    sheet_json = Column(JSON, default=dict)

    # Lore fields (shared with DND)
    personality_traits = Column(Text, default="")
    ideals = Column(Text, default="")
    bonds = Column(Text, default="")
    flaws = Column(Text, default="")
    appearance = Column(Text, default="")
    backstory = Column(Text, default="")
    goals = Column(Text, default="")
    notes = Column(Text, default="")

    portrait_url = Column(String(500), default="")

    # Versioning
    schema_version = Column(Integer, default=1)
    state_version = Column(Integer, default=1)

    __table_args__ = (
        UniqueConstraint("campaign_id", "name", name="uq_char_campaign_name"),
    )
