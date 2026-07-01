"""Campaign-scoped exact, full-text, and profile-aware BGE rule retrieval.

Dense vector search requires ChromaDB (set ``CHROMA_DB_DISABLED=0`` to enable).
Without ChromaDB, search falls back to lexical-only mode automatically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from ..db.database import Database


_DENSE_DISABLED = os.environ.get("COC7_DENSE_DISABLED", "1") != "0"


@dataclass(frozen=True)
class RuleSearchHit:
    rank: int
    score: float
    chunk_id: str
    rule_set: str
    publication: str
    breadcrumb: str
    heading: str
    text: str
    source_path: str
    start_line: int | None
    end_line: int | None
    char_start: int | None
    char_end: int | None
    citation: str
    channels: tuple[str, ...]


class RuleSearchService:
    """Retrieve only rules enabled by the current campaign profile."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def search(
        self,
        query: str,
        *,
        campaign_id: str | None = None,
        rule_set_id: str | None = None,
        publication_ids: list[str] | None = None,
        top_k: int = 5,
        dense: bool = True,
    ) -> list[RuleSearchHit]:
        """Three-tier rule search with RRF fusion."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")
        # Stub implementation — returns empty results
        return []

    def expand(self, chunk_id: str, *, mode: str = "section") -> dict[str, Any]:
        """Expand a chunk to full section context."""
        if mode not in {"chunk", "paragraph", "section", "section-with-children"}:
            raise ValueError("unsupported expansion mode")
        # Stub implementation
        return {"chunk_id": chunk_id, "text": ""}
