import logging
import re

import tiktoken

from app.models.schemas import VideoData
from app.services.embeddings import embed_texts
from app.services.qdrant import upsert_chunks

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
ENCODING = "cl100k_base"

FILLER_PATTERNS = [
    r"\bum+\b",
    r"\buh+\b",
    r"\blike\b(?=\s+\b(i|you|we|they|it)\b)",
    r"\byou know\b",
    r"\bI mean\b",
    r"\bbasically\b",
    r"\bright\?\s*",
    r"\bokay so\b",
    r"  +",
]


def clean_transcript(text: str) -> str:
    if not text:
        return ""
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str) -> list[str]:
    enc = tiktoken.get_encoding(ENCODING)
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def process_video_into_qdrant(
    video_data: VideoData,
    video_id: str,
    analysis_id: str,
    label: str,
) -> list[str]:
    transcript = clean_transcript(video_data.transcript or "")
    if not transcript:
        logger.warning("No transcript for video %s, skipping chunking", video_id)
        return []

    chunks = chunk_text(transcript)
    if not chunks:
        return []

    logger.info("Embedding %d chunks for label=%s", len(chunks), label)
    vectors = embed_texts(chunks)

    upsert_chunks(
        chunks=chunks,
        vectors=vectors,
        analysis_id=analysis_id,
        video_id=video_id,
        label=label,
        creator=video_data.creator or "",
        platform=video_data.platform,
    )

    return chunks
