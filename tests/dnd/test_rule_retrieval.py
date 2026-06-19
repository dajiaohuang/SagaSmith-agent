"""Hierarchical SRD ingestion and hybrid rule retrieval tests."""

from __future__ import annotations

from pathlib import Path

from nanobot.dnd.db import CampaignService, Database, sqlite_database_url
from nanobot.dnd.db.models import RuleChunk, RulePublication, RuleSection, RuleSet, RuleSource
from nanobot.dnd.rules.ingest import RuleIngestService
from nanobot.dnd.rules.parser import parse_markdown
from nanobot.dnd.rules.search import RuleSearchService, _enrich_query


class FakeEmbedder:
    model_name = "test/fake-bge-m3"
    dimensions = 3

    def encode(self, texts):
        vectors = []
        for text in texts:
            folded = text.casefold()
            if "grappl" in folded or "抓" in folded:
                vectors.append([1.0, 0.0, 0.0])
            elif "fireball" in folded or "火球" in folded:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def _write_fixture(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "DND5eSRD_001-018.md").write_text(
        """# Combat

## Grappling

When you take the Attack action, you can make a grapple attempt. The target makes a save.

### Escaping a Grapple

A grappled creature can attempt to escape.

# Spell Descriptions

### Fireball

Fireball creates an explosion of flame and deals fire damage.
""",
        encoding="utf-8",
    )


def test_parser_preserves_heading_tree_and_source_positions() -> None:
    text = "# Combat\n\n## Grappling\n\nRules here.\n\n### Escape\n\nEscape text.\n"
    sections, chunks = parse_markdown(text, max_chunk_chars=100)

    grapple = next(section for section in sections if section.title == "Grappling")
    escape = next(section for section in sections if section.title == "Escape")
    assert escape.parent_key == grapple.key
    assert escape.heading_path == ("Combat", "Grappling", "Escape")
    assert text[chunks[-1].char_start : chunks[-1].char_end] == "Escape text."


def test_chinese_table_terms_are_expanded_for_english_srd() -> None:
    enriched = _enrich_query("法师怎么摆脱擒抱状态")
    assert "Wizard" in enriched
    assert "Grappled" in enriched


def test_ingest_search_expand_and_incremental_skip(tmp_path: Path) -> None:
    references = tmp_path / "references"
    _write_fixture(references)
    database = Database(sqlite_database_url(tmp_path / "rules.db"))
    database.upgrade_schema()
    try:
        embedder = FakeEmbedder()
        ingest = RuleIngestService(database, embedder=embedder)
        first = ingest.ingest_srd(references)
        second = ingest.ingest_srd(references)
        assert first.sources_indexed == 1
        assert first.chunks >= 3
        assert first.embeddings == first.chunks
        assert second.sources_skipped == 1

        campaign = CampaignService(database).create("Rules", campaign_id="rules-campaign")
        # Campaigns created after indexing automatically pin the core publication.
        search = RuleSearchService(database, embedder=embedder)

        exact = search.search("Fireball", campaign_id=campaign.id, dense=False)
        assert exact and exact[0].heading == "Fireball"
        assert "exact" in exact[0].channels
        assert "chars" in exact[0].citation

        lexical = search.search("grappled creature escape", campaign_id=campaign.id, dense=False)
        assert lexical and "lexical" in lexical[0].channels

        semantic = search.search("怎么抓住敌人", campaign_id=campaign.id, dense=True)
        assert semantic and semantic[0].heading in {"Grappling", "Escaping a Grapple"}
        assert "dense" in semantic[0].channels

        expanded = search.expand(exact[0].chunk_id, mode="section")
        assert "explosion of flame" in expanded["text"]
        assert expanded["breadcrumb"].endswith("Fireball")

        with database.transaction() as session:
            session.add(
                RuleSet(
                    id="alternate-rules",
                    game_system="D&D 5e",
                    edition="Homebrew",
                    release="1",
                    locale="en",
                )
            )
            session.flush()
            session.add(
                RulePublication(
                    id="alternate-book",
                    rule_set_id="alternate-rules",
                    name="Alternate Book",
                    slug="alternate-book",
                    publication_type="core",
                )
            )
            session.flush()
            session.add(
                RuleSource(
                    id="alternate-source",
                    rule_set_id="alternate-rules",
                    publication_id="alternate-book",
                    name="Alternate",
                    source_path="alternate/fireball.md",
                    source_type="markdown",
                    locale="en",
                    metadata_json={},
                )
            )
            session.flush()
            session.add(
                RuleSection(
                    id="alternate-section",
                    source_id="alternate-source",
                    publication_id="alternate-book",
                    parent_id=None,
                    title="Fireball",
                    slug="fireball",
                    path="fireball",
                    heading_path=["Fireball"],
                    depth=1,
                    order_index=0,
                )
            )
            session.flush()
            session.add(
                RuleChunk(
                    id="alternate-chunk",
                    source_id="alternate-source",
                    section_id="alternate-section",
                    chunk_index=0,
                    heading="Fireball",
                    breadcrumb="Fireball",
                    token_count=4,
                    content_hash="alternate",
                    chunk_text="Alternate campaign-only fireball rule.",
                    search_text="Fireball alternate campaign-only rule",
                    embedding_json=[0.0, 1.0, 0.0],
                    metadata_json={},
                )
            )

        alternate = CampaignService(database).create("Alternate", campaign_id="alternate")
        ingest.bind_campaign(
            alternate.id,
            rule_set_id="alternate-rules",
            publication_ids=["alternate-book"],
        )
        original_hit = search.search("Fireball", campaign_id=campaign.id, dense=False)[0]
        alternate_hit = search.search("Fireball", campaign_id=alternate.id, dense=False)[0]
        assert "explosion of flame" in original_hit.text
        assert "campaign-only" in alternate_hit.text
    finally:
        database.dispose()
