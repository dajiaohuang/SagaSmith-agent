from sqlalchemy import select, text

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import RuleChunk
from app.rag.embedder import embed_texts


def reindex_rules() -> int:
    with SessionLocal() as db:
        chunks = list(db.scalars(select(RuleChunk).order_by(RuleChunk.id)).all())
        batch_size = settings.embedding_batch_size
        completed = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            vectors = embed_texts([chunk.chunk_text for chunk in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                chunk.embedding = vector
                if vector and db.bind and db.bind.dialect.name == "postgresql":
                    literal = "[" + ",".join(str(value) for value in vector) + "]"
                    db.execute(
                        text("UPDATE rule_chunks SET embedding_vector = CAST(:vector AS vector) WHERE id = :id"),
                        {"vector": literal, "id": chunk.id},
                    )
            db.commit()
            completed += len(batch)
            print(f"Embedded {completed}/{len(chunks)} rule chunks")
        return completed


if __name__ == "__main__":
    print(f"Reindexed {reindex_rules()} rule chunks with {settings.embedding_model}")

