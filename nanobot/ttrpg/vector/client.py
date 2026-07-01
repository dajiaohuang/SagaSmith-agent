"""Shared ChromaDB client lifecycle and collection access for all TTRPG systems.

One ``VectorStore`` singleton serves all systems.  Collection names are scoped
by system prefix (``dnd_*``, ``coc7_*``) to keep indices isolated.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from chromadb import Collection, HttpClient, PersistentClient
from chromadb.config import Settings

from nanobot.ttrpg._paths import get_runtime_subdir

if TYPE_CHECKING:
    from nanobot.ttrpg.rules.embedding import EmbeddingProfile

logger = logging.getLogger(__name__)

_COLLECTION_METADATA = {
    "hnsw:space": "cosine",
}


class VectorStore:
    """Manage a ChromaDB client and provide collection access.

    Usage::

        store = VectorStore()
        if store.enabled:
            coll = store.collection("dnd_rules")
            coll.query(...)
    """

    _instance: VectorStore | None = None

    def __new__(cls) -> VectorStore:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client: HttpClient | PersistentClient | None = None
            cls._instance._collections: dict[str, Collection] = {}
            cls._instance._enabled: bool | None = None
        return cls._instance

    @property
    def enabled(self) -> bool:
        """True when ChromaDB is configured and reachable."""
        if self._enabled is None:
            url = os.environ.get("CHROMA_DB_URL")
            path = os.environ.get("CHROMA_DB_PATH")
            self._enabled = bool(url or path)
        return self._enabled

    @staticmethod
    def configured_url() -> str | None:
        """Return the configured HTTP URL, if any."""
        return os.environ.get("CHROMA_DB_URL") or None

    @staticmethod
    def configured_path() -> Path | None:
        """Return the configured persistent path, if any."""
        raw = os.environ.get("CHROMA_DB_PATH")
        return Path(raw).expanduser().resolve() if raw else None

    def _connect(self) -> HttpClient | PersistentClient:
        url = self.configured_url()
        if url:
            logger.info("Connecting to ChromaDB HTTP server at %s", url)
            return HttpClient(host=url, settings=Settings(anonymized_telemetry=False))
        path = self.configured_path() or get_runtime_subdir("chroma_db")
        path.mkdir(parents=True, exist_ok=True)
        logger.info("Opening ChromaDB persistent store at %s", path)
        return PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))

    def _ensure_client(self):
        if self._client is None:
            self._client = self._connect()
        return self._client

    def collection(self, name: str) -> Collection:
        """Return a ChromaDB collection, creating it on first access."""
        if name not in self._collections:
            client = self._ensure_client()
            self._collections[name] = client.get_or_create_collection(
                name=name,
                metadata=_COLLECTION_METADATA,
            )
        return self._collections[name]

    def collection_for(self, base_name: str, profile: EmbeddingProfile) -> Collection:
        """Return a model-isolated collection and validate its manifest."""
        from nanobot.ttrpg.rules.embedding import collection_name

        name = collection_name(base_name, profile)
        if name not in self._collections:
            client = self._ensure_client()
            expected = {
                **_COLLECTION_METADATA,
                "embedding_model": profile.model_name,
                "embedding_dimensions": profile.dimensions,
                "embedding_language": profile.language,
                "embedding_index_version": 1,
            }
            collection = client.get_or_create_collection(name=name, metadata=expected)
            metadata = collection.metadata or {}
            for key in (
                "embedding_model",
                "embedding_dimensions",
                "embedding_language",
                "embedding_index_version",
            ):
                if metadata.get(key) != expected[key]:
                    raise RuntimeError(
                        f"ChromaDB collection {name!r} has an incompatible embedding "
                        f"manifest ({key}={metadata.get(key)!r}, expected {expected[key]!r}); "
                        "rebuild the collection before querying it"
                    )
            self._collections[name] = collection
        return self._collections[name]

    def collection_stats(self, name: str) -> dict:
        """Return approximate row count for a collection."""
        try:
            coll = self.collection(name)
            return {"name": name, "count": coll.count()}
        except Exception as exc:
            return {"name": name, "count": None, "error": str(exc)}

    def drop_collection(self, name: str) -> None:
        """Delete a collection entirely (used by reindex)."""
        if name in self._collections:
            self._collections.pop(name)
        try:
            self._ensure_client().delete_collection(name)
        except Exception:
            logger.debug("Collection %r does not exist or could not be deleted", name)

    def dispose(self) -> None:
        """Release client resources."""
        self._collections.clear()
        self._client = None
