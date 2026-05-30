import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.features.ingestion.service import get_progress_queue, run_analysis_pipeline
from app.models.db import Analysis, Video
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, AnalysisResponse, VideoCardResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["ingestion"])


@router.post("", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    analysis_id = str(uuid.uuid4())
    analysis = Analysis(
        id=analysis_id,
        video_a_id=None,  # type: ignore[arg-type]
        video_b_id=None,  # type: ignore[arg-type]
        status="processing",
    )
    db.add(analysis)
    await db.commit()

    background_tasks.add_task(run_analysis_pipeline, analysis_id, request.video_a_url, request.video_b_url)
    return AnalyzeResponse(analysis_id=analysis_id)


@router.get("/progress/{analysis_id}")
async def progress(analysis_id: str) -> StreamingResponse:
    queue = get_progress_queue(analysis_id)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("done"):
                        break
                except asyncio.TimeoutError:
                    yield "data: {\"heartbeat\": true}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    video_a = None
    video_b = None

    if analysis.video_a_id:
        res = await db.execute(select(Video).where(Video.id == analysis.video_a_id))
        v = res.scalar_one_or_none()
        if v:
            video_a = VideoCardResponse(
                id=v.id,
                platform=v.platform,
                url=v.url,
                title=v.title,
                creator=v.creator,
                followers=v.followers,
                views=v.views,
                likes=v.likes,
                comments=v.comments,
                engagement_rate=v.engagement_rate,
                duration=v.duration,
                upload_date=v.upload_date,
                hashtags=v.hashtags or [],
                thumbnail_url=v.thumbnail_url,
            )

    if analysis.video_b_id:
        res = await db.execute(select(Video).where(Video.id == analysis.video_b_id))
        v = res.scalar_one_or_none()
        if v:
            video_b = VideoCardResponse(
                id=v.id,
                platform=v.platform,
                url=v.url,
                title=v.title,
                creator=v.creator,
                followers=v.followers,
                views=v.views,
                likes=v.likes,
                comments=v.comments,
                engagement_rate=v.engagement_rate,
                duration=v.duration,
                upload_date=v.upload_date,
                hashtags=v.hashtags or [],
                thumbnail_url=v.thumbnail_url,
            )

    # Use model_validate so dicts from DB are coerced to typed Pydantic models
    return AnalysisResponse.model_validate({
        "id": analysis.id,
        "status": analysis.status,
        "video_a": video_a,
        "video_b": video_b,
        "hook_analysis_a": analysis.hook_analysis_a,
        "hook_analysis_b": analysis.hook_analysis_b,
        "structure_a": analysis.structure_a,
        "structure_b": analysis.structure_b,
        "viral_patterns_a": analysis.viral_patterns_a,
        "viral_patterns_b": analysis.viral_patterns_b,
        "recommendations": analysis.recommendations,
        "comparison_insights": analysis.comparison_insights,
        "error_message": analysis.error_message,
    })
