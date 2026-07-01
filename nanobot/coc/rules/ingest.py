"""Incremental hierarchical rule ingestion with configurable BGE embeddings."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..db.database import Database


DEFAULT_RULE_SET_ID = "coc7e-srd-1.0"
DEFAULT_PUBLICATION_ID = "publication-srd-1.0"


@dataclass(frozen=True)
class IngestResult:
    rule_set_id: str
    publication_id: str
    sources_indexed: int
    sources_skipped: int
    sections: int
    chunks: int
    embeddings: int


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def ensure_bundled_rules_ingested(database: Database) -> dict[str, IngestResult]:
    """Auto-ingest bundled CoC7 SRD if not already present.

    Returns an empty dict when no bundled CoC7 rules are found (stub).
    """
    return {}
