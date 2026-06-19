"""Complete campaign snapshot save, restore, isolation, and undo tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from nanobot.dnd.db import CampaignSnapshotService, Database, UndoManager, sqlite_database_url
from nanobot.dnd.db.models import (
    Campaign,
    CampaignEvent,
    Character,
    Combat,
    Party,
    PlotSummary,
    WorldState,
)
from nanobot.dnd.db.snapshots import InvalidSnapshotError


@pytest.fixture
def database(tmp_path: Path) -> Database:
    db = Database(sqlite_database_url(tmp_path / "snapshots.db"))
    db.upgrade_schema()
    try:
        yield db
    finally:
        db.dispose()


def _seed_campaign(database: Database, campaign_id: str, *, day: int) -> None:
    with database.transaction() as session:
        session.add(Campaign(id=campaign_id, name=f"Campaign {campaign_id}"))
        session.flush()
        session.add(
            WorldState(
                id=f"world_{campaign_id}",
                campaign_id=campaign_id,
                state_json={"day_in_game": day, "current_chapter": 1},
                state_version=day,
            )
        )
        session.add(
            Party(
                id=f"party_{campaign_id}",
                campaign_id=campaign_id,
                location="Tavern",
                state_json={"gold": 10},
            )
        )
        session.flush()
        session.add(
            Character(
                id=f"character_{campaign_id}",
                campaign_id=campaign_id,
                party_id=f"party_{campaign_id}",
                name="Hero",
                hp=10,
                max_hp=10,
                sheet_json={"inventory": ["rope"]},
            )
        )
        session.add(
            PlotSummary(
                id=f"summary_{campaign_id}",
                campaign_id=campaign_id,
                summary="The party met.",
            )
        )
        session.add(
            CampaignEvent(
                id=f"event_{campaign_id}",
                campaign_id=campaign_id,
                event_type="start",
                content="Campaign started",
            )
        )


def test_complete_snapshot_restores_all_current_state(database: Database) -> None:
    _seed_campaign(database, "one", day=1)
    service = CampaignSnapshotService(database)
    saved = service.create("one", label="Before battle", actor_id="dm")

    with database.transaction() as session:
        world = session.get(WorldState, "world_one")
        world.state_json = {"day_in_game": 9, "current_chapter": 2}
        hero = session.get(Character, "character_one")
        hero.hp = 1
        hero.sheet_json = {"inventory": []}
        session.add(
            Combat(
                id="combat_later",
                campaign_id="one",
                name="Later combat",
                state_json={"round": 3},
            )
        )
        session.add(
            CampaignEvent(
                id="event_later",
                campaign_id="one",
                event_type="later",
                content="Should disappear on load",
            )
        )

    restored = service.restore("one", saved.slot, actor_id="dm")

    with database.transaction() as session:
        world = session.get(WorldState, "world_one")
        hero = session.get(Character, "character_one")
        assert world.state_json["day_in_game"] == 1
        assert hero.hp == 10
        assert hero.sheet_json["inventory"] == ["rope"]
        assert session.scalar(select(Combat).where(Combat.campaign_id == "one")) is None
        events = list(
            session.scalars(
                select(CampaignEvent).where(CampaignEvent.campaign_id == "one")
            )
        )
        assert [event.id for event in events] == ["event_one"]
        assert restored.audit_id.startswith("audit_restore_")


def test_campaign_snapshots_are_isolated(database: Database) -> None:
    _seed_campaign(database, "one", day=1)
    _seed_campaign(database, "two", day=2)
    service = CampaignSnapshotService(database)
    one = service.create("one")
    two = service.create("two")

    assert one.slot == 1
    assert two.slot == 1
    with pytest.raises(InvalidSnapshotError, match="different campaign"):
        payload = service.get("one", one.slot)
        payload["campaign_id"] = "two"
        CampaignSnapshotService.validate(payload, expected_campaign_id="one")

    service.restore("one", one.slot)
    with database.transaction() as session:
        assert session.get(WorldState, "world_two").state_json["day_in_game"] == 2


def test_snapshot_restore_can_be_undone(database: Database) -> None:
    _seed_campaign(database, "one", day=1)
    service = CampaignSnapshotService(database)
    saved = service.create("one")
    with database.transaction() as session:
        world = session.get(WorldState, "world_one")
        world.state_json = {"day_in_game": 5, "current_chapter": 2}

    service.restore("one", saved.slot)
    result = UndoManager(database).undo("one")

    assert result.count == 1
    with database.transaction() as session:
        assert session.get(WorldState, "world_one").state_json["day_in_game"] == 5
