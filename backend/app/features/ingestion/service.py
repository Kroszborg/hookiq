import asyncio
import hashlib
import logging
import uuid
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.features.ingestion.instagram import extract_instagram
from app.features.ingestion.pipeline import process_video_into_qdrant
from app.features.ingestion.youtube import extract_youtube
from app.features.intelligence.analyzer import run_full_analysis
from app.models.db import Analysis, Video
from app.models.schemas import VideoData
from app.services.qdrant import ensure_collection

logger = logging.getLogger(__name__)

PROGRESS_STEPS = [
    "Extracting metadata",
    "Fetching transcript",
    "Processing content",
    "Generating embeddings",
    "Storing vectors",
    "Building intelligence layer",
]

# analysis_id → asyncio.Queue for SSE progress
_progress_queues: dict[str, asyncio.Queue] = {}


def get_progress_queue(analysis_id: str) -> asyncio.Queue:
    if analysis_id not in _progress_queues:
        _progress_queues[analysis_id] = asyncio.Queue()
    return _progress_queues[analysis_id]


def cleanup_progress_queue(analysis_id: str) -> None:
    _progress_queues.pop(analysis_id, None)


async def _emit(queue: asyncio.Queue, step: str, index: int, done: bool = False, error: str | None = None) -> None:
    await queue.put({"step": step, "index": index, "total": len(PROGRESS_STEPS), "done": done, "error": error})


async def _get_or_create_video(
    db: AsyncSession,
    url: str,
    platform: str,
) -> tuple[Video | None, bool]:
    url_hash = hashlib.sha256(url.strip().encode()).hexdigest()
    result = await db.execute(select(Video).where(Video.url_hash == url_hash))
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("Cache hit for URL hash %s", url_hash)
        return existing, True
    return None, False


async def _save_video(db: AsyncSession, video_data: VideoData) -> Video:
    video = Video(
        id=str(uuid.uuid4()),
        platform=video_data.platform,
        url=video_data.url,
        url_hash=video_data.url_hash,
        title=video_data.title,
        creator=video_data.creator,
        followers=video_data.followers,
        views=video_data.views,
        likes=video_data.likes,
        comments=video_data.comments,
        engagement_rate=video_data.engagement_rate,
        duration=video_data.duration,
        upload_date=video_data.upload_date,
        hashtags=video_data.hashtags,
        transcript=video_data.transcript,
        thumbnail_url=video_data.thumbnail_url,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def run_analysis_pipeline(analysis_id: str, url_a: str, url_b: str) -> None:
    queue = get_progress_queue(analysis_id)

    async with async_session_maker() as db:
        try:
            ensure_collection()

            await _emit(queue, PROGRESS_STEPS[0], 0)
            await _emit(queue, PROGRESS_STEPS[1], 1)

            # detect platforms
            def detect_platform(url: str) -> str:
                if "instagram.com" in url:
                    return "instagram"
                return "youtube"

            platform_a = detect_platform(url_a)
            platform_b = detect_platform(url_b)

            extractor_a = extract_instagram if platform_a == "instagram" else extract_youtube
            extractor_b = extract_instagram if platform_b == "instagram" else extract_youtube

            video_a_data, video_b_data = await asyncio.gather(
                extractor_a(url_a),
                extractor_b(url_b),
            )

            await _emit(queue, PROGRESS_STEPS[2], 2)

            # Check cache
            cached_a_result = await db.execute(select(Video).where(Video.url_hash == video_a_data.url_hash))
            video_a_db = cached_a_result.scalar_one_or_none()
            if not video_a_db:
                video_a_db = await _save_video(db, video_a_data)

            cached_b_result = await db.execute(select(Video).where(Video.url_hash == video_b_data.url_hash))
            video_b_db = cached_b_result.scalar_one_or_none()
            if not video_b_db:
                video_b_db = await _save_video(db, video_b_data)

            await _emit(queue, PROGRESS_STEPS[3], 3)

            # Embed and store in Qdrant
            await asyncio.gather(
                process_video_into_qdrant(video_a_data, video_a_db.id, analysis_id, "A"),
                process_video_into_qdrant(video_b_data, video_b_db.id, analysis_id, "B"),
            )

            await _emit(queue, PROGRESS_STEPS[4], 4)

            # Run intelligence analysis
            await _emit(queue, PROGRESS_STEPS[5], 5)
            intelligence = await run_full_analysis(video_a_data, video_b_data)

            # Update analysis record
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one()
            analysis.video_a_id = video_a_db.id
            analysis.video_b_id = video_b_db.id
            analysis.status = "complete"
            analysis.hook_analysis_a = intelligence.get("hook_a")
            analysis.hook_analysis_b = intelligence.get("hook_b")
            analysis.structure_a = intelligence.get("structure_a")
            analysis.structure_b = intelligence.get("structure_b")
            analysis.viral_patterns_a = intelligence.get("viral_a")
            analysis.viral_patterns_b = intelligence.get("viral_b")
            analysis.recommendations = intelligence.get("recommendations")
            analysis.comparison_insights = intelligence.get("comparison")
            await db.commit()

            await _emit(queue, "Complete", len(PROGRESS_STEPS), done=True)
            logger.info("Analysis %s completed successfully", analysis_id)

        except Exception as e:
            logger.exception("Pipeline failed for analysis %s: %s", analysis_id, e)
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = str(e)
                await db.commit()
            await _emit(queue, "Failed", 0, done=True, error=str(e))
        finally:
            await asyncio.sleep(5)
            cleanup_progress_queue(analysis_id)
