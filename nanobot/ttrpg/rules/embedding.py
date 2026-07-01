"""Shared BGE embedding profiles, language routing, and lazy model loading.

Both D&D and CoC use the same embedding infrastructure.  Each system registers
its own profiles via the ``TTTPG_EMBEDDING_PROFILES`` pattern.
"""

from __future__ import annotations

import os
import re
import threading
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Protocol

DEFAULT_BGE_M3_MODEL = "BAAI/bge-m3"
DEFAULT_BGE_SMALL_EN_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_DIMENSIONS = 1024


@dataclass(frozen=True)
class EmbeddingProfile:
    key: str
    model_name: str
    dimensions: int
    language: str

    @property
    def model_id(self) -> str:
        return f"embedding-{self.key.replace('_', '-')}"


BGE_M3_PROFILE = EmbeddingProfile("bge_m3", DEFAULT_BGE_M3_MODEL, 1024, "multi")
BGE_SMALL_EN_PROFILE = EmbeddingProfile(
    "bge_small_en_v1_5", DEFAULT_BGE_SMALL_EN_MODEL, 384, "en"
)
EMBEDDING_PROFILES = {
    profile.key: profile
    for profile in (BGE_M3_PROFILE, BGE_SMALL_EN_PROFILE)
}
_PROFILES_BY_MODEL = {profile.model_name: profile for profile in EMBEDDING_PROFILES.values()}
_PROFILE_ALIASES = {
    "m3": BGE_M3_PROFILE.key,
    "bge-m3": BGE_M3_PROFILE.key,
    "en": BGE_SMALL_EN_PROFILE.key,
    "small-en": BGE_SMALL_EN_PROFILE.key,
}


# ── Helpers ────────────────────────────────────────────────────────────


def collection_name(base_name: str, profile: EmbeddingProfile) -> str:
    return f"{base_name}__{profile.key}"


def cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except (ImportError, RuntimeError):
        return False


def embedding_mode(env_prefix: str = "TTRPG") -> str:
    configured = os.environ.get(f"{env_prefix}_EMBEDDING_MODE", "auto").strip().lower()
    if configured not in {"auto", "cpu", "gpu"}:
        raise ValueError(f"{env_prefix}_EMBEDDING_MODE must be 'auto', 'cpu', or 'gpu'")
    if configured == "auto":
        return "gpu" if cuda_available() else "cpu"
    if configured == "gpu" and not cuda_available():
        raise RuntimeError(
            f"{env_prefix}_EMBEDDING_MODE=gpu was requested but CUDA is unavailable"
        )
    return configured


def normalize_language(language: str | None) -> str:
    value = (language or "").strip().lower().replace("_", "-")
    if value.startswith(("zh", "cn")):
        return "zh"
    if value.startswith("en"):
        return "en"
    return "mixed"


def detect_text_language(text: str) -> str:
    cjk_count = len(re.findall(r"[㐀-䶿一-鿿]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if cjk_count and latin_count:
        smaller = min(cjk_count, latin_count)
        larger = max(cjk_count, latin_count)
        if smaller / larger >= 0.15:
            return "mixed"
    if cjk_count:
        return "zh"
    if latin_count:
        return "en"
    return "mixed"


def resolve_profile(name: str) -> EmbeddingProfile:
    key = _PROFILE_ALIASES.get(name.strip().lower(), name.strip().lower())
    if key in EMBEDDING_PROFILES:
        return EMBEDDING_PROFILES[key]
    raise ValueError(f"unknown profile {name!r}")


def profile_for_model(model_name: str, env_prefix: str = "TTRPG") -> EmbeddingProfile:
    profile = _PROFILES_BY_MODEL.get(model_name)
    if profile is not None:
        return profile
    dimensions = int(os.environ.get(f"{env_prefix}_EMBEDDING_DIMENSIONS", "1024"))
    key = re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_")
    return EmbeddingProfile(key or "custom", model_name, dimensions, "multi")


def profile_for_language(
    language: str | None,
    profiles: tuple[EmbeddingProfile, ...] | None = None,
) -> EmbeddingProfile:
    if profiles is None:
        profiles = tuple(EMBEDDING_PROFILES.values())
    if len(profiles) == 1:
        return profiles[0]
    normalized = normalize_language(language)
    matching = [p for p in profiles if p.language in {normalized, "multi"}]
    if matching:
        language_specific = [p for p in matching if p.language == normalized]
        return (language_specific or matching)[0]
    return profiles[0]


# ── Embedder protocol + BGE-M3 implementation ──────────────────────────


class Embedder(Protocol):
    model_name: str
    dimensions: int
    profile: EmbeddingProfile
    model_id: str

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class BgeM3Embedder:
    """Load one BGE profile on first use and return normalized dense vectors."""

    _models: ClassVar[dict[tuple[str, str | None], object]] = {}
    _model_lock: ClassVar[threading.Lock] = threading.Lock()
    _vector_cache: ClassVar[OrderedDict[tuple[str, str], list[float]]] = OrderedDict()
    _vector_cache_lock: ClassVar[threading.Lock] = threading.Lock()
    _vector_cache_size: ClassVar[int] = 256

    def __init__(
        self,
        model_name: str | None = None,
        *,
        device: str | None = None,
        language: str | None = None,
        profile: EmbeddingProfile | None = None,
        batch_size: int | None = None,
        show_progress: bool = False,
        env_prefix: str = "TTRPG",
    ) -> None:
        configured_model = model_name or os.environ.get(f"{env_prefix}_EMBEDDING_MODEL")
        if profile is not None and configured_model and profile.model_name != configured_model:
            raise ValueError("profile and model_name refer to different embedding models")
        self.profile = (
            profile
            or (profile_for_model(configured_model, env_prefix) if configured_model else None)
            or profile_for_language(language)
        )
        self.model_name = self.profile.model_name
        self.dimensions = self.profile.dimensions
        self.model_id = self.profile.model_id
        configured_device = device or os.environ.get(f"{env_prefix}_EMBEDDING_DEVICE")
        if configured_device:
            self.device = configured_device
        elif embedding_mode(env_prefix) == "gpu":
            self.device = "cuda"
        else:
            self.device = "cpu"
        self.batch_size = batch_size or int(
            os.environ.get(f"{env_prefix}_EMBEDDING_BATCH_SIZE", "8")
        )
        self.show_progress = show_progress

    def _load(self):
        key = (self.model_name, self.device)
        model = self._models.get(key)
        if model is None:
            with self._model_lock:
                model = self._models.get(key)
                if model is not None:
                    return model
                from sentence_transformers import SentenceTransformer

                kwargs = {"device": self.device} if self.device else {}
                model = SentenceTransformer(self.model_name, **kwargs)
                get_dimension = getattr(model, "get_embedding_dimension", None)
                if get_dimension is None:
                    get_dimension = model.get_sentence_embedding_dimension
                dimension = get_dimension()
                if dimension != self.dimensions:
                    raise RuntimeError(
                        f"{self.model_name} returned {dimension} dimensions; "
                        f"expected {self.dimensions}"
                    )
                self._models[key] = model
        return model

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        normalized = [str(text) for text in texts]
        results: list[list[float] | None] = [None] * len(normalized)
        missing_texts: list[str] = []
        missing_indexes: list[int] = []
        with self._vector_cache_lock:
            for index, value in enumerate(normalized):
                cache_key = (self.model_name, value)
                cached = self._vector_cache.get(cache_key)
                if cached is None:
                    missing_texts.append(value)
                    missing_indexes.append(index)
                else:
                    self._vector_cache.move_to_end(cache_key)
                    results[index] = list(cached)

        if not missing_texts:
            return [row for row in results if row is not None]

        vectors = self._load().encode(
            missing_texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=self.show_progress,
        )
        encoded = [row.astype("float32").tolist() for row in vectors]
        with self._vector_cache_lock:
            for index, value, vector in zip(missing_indexes, missing_texts, encoded, strict=True):
                results[index] = vector
                cache_key = (self.model_name, value)
                self._vector_cache[cache_key] = vector
                self._vector_cache.move_to_end(cache_key)
            while len(self._vector_cache) > self._vector_cache_size:
                self._vector_cache.popitem(last=False)
        return [row for row in results if row is not None]
