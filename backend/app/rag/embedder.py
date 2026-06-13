from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    device = None if settings.embedding_device == "auto" else settings.embedding_device
    return SentenceTransformer(settings.embedding_model, device=device)


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    if not texts:
        return []
    if settings.embedding_backend == "disabled":
        return [None] * len(texts)
    vectors = get_embedding_model().encode(
        texts,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [vector.tolist() for vector in vectors]


def embed_text(text: str) -> list[float] | None:
    try:
        return embed_texts([text])[0]
    except Exception:
        return None
