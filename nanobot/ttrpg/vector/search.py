"""Shared ChromaDB dense-vector search helper for all TTRPG systems."""

from __future__ import annotations

import logging
from typing import Any

from nanobot.ttrpg.rules.embedding import EmbeddingProfile
from nanobot.ttrpg.vector.client import VectorStore

logger = logging.getLogger(__name__)


def chroma_dense_search(
    collection_name: str,
    query_vector: list[float],
    where: dict[str, Any] | None = None,
    *,
    profile: EmbeddingProfile | None = None,
    limit: int = 50,
) -> list[tuple[str, float]]:
    """Search a ChromaDB collection and return ``(chunk_id, similarity)`` pairs.

    Args:
        collection_name: e.g. ``"dnd_rules"``, ``"coc7_modules"``.
        query_vector: Normalised embedding vector.
        where: Optional ChromaDB metadata filter dict.
        profile: Optional embedding profile for model-isolated collections.
        limit: Maximum number of results.

    Returns:
        List of ``(chunk_id, similarity_score)`` ordered by descending similarity.
    """
    store = VectorStore()
    if not store.enabled:
        logger.warning("ChromaDB is not configured; dense search is unavailable")
        return []

    try:
        coll = (
            store.collection_for(collection_name, profile)
            if profile is not None
            else store.collection(collection_name)
        )
    except Exception:
        logger.exception("Failed to access ChromaDB collection %r", collection_name)
        return []

    try:
        results = coll.query(
            query_embeddings=[query_vector],
            n_results=min(limit, coll.count()),
            where=where,
            include=["distances"],
        )
    except Exception:
        logger.exception("ChromaDB query failed on collection %r", collection_name)
        return []

    ids = results.get("ids")
    distances = results.get("distances")
    if not ids or not distances or not ids[0]:
        return []

    chunk_ids: list[str] = ids[0]
    distance_list: list[float] = distances[0]

    return [
        (chunk_id, 1.0 - float(dist))
        for chunk_id, dist in zip(chunk_ids, distance_list)
    ]
