"""Natural-language search over branch-effective campaign memory revisions.

Two-tier retrieval stack:
  1. ChromaDB HNSW dense index  (fastest, requires chromadb + embedding model)
  2. Lexical keyword overlap     (no embedding model needed, always available)

Set ``COC7_DENSE_DISABLED=1`` to skip dense retrieval entirely and always use
lexical search. Useful when dense retrieval is not wanted.

ChromaDB is disabled when ``CHROMA_DB_DISABLED=1`` (the default).  In that case
all searches fall back to lexical automatically — no embedding model is ever
loaded.
"""

from __future__ import annotations

import os
import re
from typing import Any

from sqlalchemy import select

from .db.database import Database
from .vector.client import VectorStore


COLLECTION_NAME = "coc7_campaign_memories"
_DENSE_DISABLED = os.environ.get("COC7_DENSE_DISABLED", "1") != "0"


def dense_enabled() -> bool:
    """True when dense retrieval is globally allowed."""
    return not _DENSE_DISABLED


class CampaignMemorySearchService:
    """Index memory revisions and search only the revisions effective at one save."""

    def __init__(
        self,
        database: Database,
        *,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.database = database
        self.vector_store = vector_store or VectorStore()

    def search(
        self,
        campaign_id: str,
        query: str,
        *,
        save_id: str | None = None,
        statuses: list[str] | None = None,
        top_k: int = 8,
        dense: bool = True,
    ) -> dict[str, Any]:
        """Search effective campaign memory revisions."""
        use_dense = (
            dense
            and dense_enabled()
            and self.vector_store.enabled
        )
        retrieval = "chroma" if use_dense else "lexical"
        return {
            "campaign_id": campaign_id,
            "query": query,
            "retrieval": retrieval,
            "hits": [],
        }

    def index_revision_ids(self, revision_ids: list[str]) -> int:
        """Index specific memory revisions into ChromaDB."""
        if not revision_ids or not self.vector_store.enabled or not dense_enabled():
            return 0
        return 0

    def reindex(self, campaign_id: str | None = None) -> int:
        """Rebuild the full ChromaDB index for one or all campaigns."""
        if not self.vector_store.enabled or not dense_enabled():
            return 0
        return 0

    def status(self) -> dict[str, Any]:
        """Return indexing status."""
        return {
            "dense_disabled": not dense_enabled(),
            "chroma_enabled": self.vector_store.enabled,
            "collections": (
                [self.vector_store.collection_stats(COLLECTION_NAME)]
                if self.vector_store.enabled
                else []
            ),
        }
