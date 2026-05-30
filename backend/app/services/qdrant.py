import logging
import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    logger.info("Connecting to Qdrant at %s", settings.QDRANT_URL)
    return QdrantClient(url=settings.QDRANT_URL, timeout=10)


def ensure_collection() -> None:
    settings = get_settings()
    # Clear cached client so we get a fresh connection if Qdrant wasn't ready earlier
    get_qdrant_client.cache_clear()
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", settings.QDRANT_COLLECTION)


def upsert_chunks(
    chunks: list[str],
    vectors: list[list[float]],
    analysis_id: str,
    video_id: str,
    label: str,
    creator: str,
    platform: str,
) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    # Ensure collection exists before upsert
    try:
        ensure_collection()
    except Exception:
        pass

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "content": chunk,
                "chunk_id": i,
                "video_id": video_id,
                "analysis_id": analysis_id,
                "label": label,
                "creator": creator,
                "source_platform": platform,
            },
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]

    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    logger.info("Upserted %d chunks for label=%s analysis=%s", len(points), label, analysis_id)


def search_chunks(
    query_vector: list[float],
    analysis_id: str,
    label: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    settings = get_settings()
    client = get_qdrant_client()

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="analysis_id", match=MatchValue(value=analysis_id)),
                FieldCondition(key="label", match=MatchValue(value=label)),
            ]
        ),
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "chunk_id": r.payload.get("chunk_id", i),
            "content": r.payload.get("content", ""),
            "label": r.payload.get("label", label),
            "score": r.score,
        }
        for i, r in enumerate(results)
    ]


def delete_analysis_chunks(analysis_id: str) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="analysis_id", match=MatchValue(value=analysis_id))]
        ),
    )
