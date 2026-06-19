"""Native D&D rules tool tests."""

from __future__ import annotations

from pathlib import Path

from nanobot.agent.tools.dnd_rules import DndRulesTool
from nanobot.dnd.db import Database, sqlite_database_url
from nanobot.dnd.rules.ingest import RuleIngestService
from nanobot.dnd.rules.search import RuleSearchService


class FakeEmbedder:
    model_name = "test/fake"
    dimensions = 3

    def encode(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


async def test_dnd_rules_tool_search_expand_and_status(tmp_path: Path) -> None:
    references = tmp_path / "references"
    references.mkdir()
    (references / "DND5eSRD_001-018.md").write_text(
        "# Combat\n\n## Grappling\n\nA grappled creature can escape.\n",
        encoding="utf-8",
    )
    database = Database(sqlite_database_url(tmp_path / "tool.db"))
    database.upgrade_schema()
    RuleIngestService(database, embedder=FakeEmbedder()).ingest_srd(references)
    tool = DndRulesTool(database, migrate=False)
    tool.search_service = RuleSearchService(database, embedder=FakeEmbedder())
    try:
        status = await tool.execute(action="status")
        assert status["chunks"] == 1
        assert status["embedded_chunks"] == 1

        result = await tool.execute(action="search", query="Grappling", dense=False)
        assert result["hits"][0]["heading"] == "Grappling"

        expanded = await tool.execute(
            action="expand",
            chunk_id=result["hits"][0]["chunk_id"],
            expand_mode="section",
        )
        assert "can escape" in expanded["text"]
    finally:
        database.dispose()
