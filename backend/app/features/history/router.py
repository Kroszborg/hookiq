import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db import Analysis, Video
from app.models.schemas import HistoryItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryItem])
async def get_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[HistoryItem]:
    result = await db.execute(
        select(Analysis)
        .where(Analysis.status.in_(["complete", "processing", "failed"]))
        .order_by(Analysis.created_at.desc())
        .limit(limit)
    )
    analyses = result.scalars().all()

    items = []
    for analysis in analyses:
        va_thumb = va_creator = vb_thumb = vb_creator = None

        if analysis.video_a_id:
            res = await db.execute(select(Video).where(Video.id == analysis.video_a_id))
            va = res.scalar_one_or_none()
            if va:
                va_thumb = va.thumbnail_url
                va_creator = va.creator

        if analysis.video_b_id:
            res = await db.execute(select(Video).where(Video.id == analysis.video_b_id))
            vb = res.scalar_one_or_none()
            if vb:
                vb_thumb = vb.thumbnail_url
                vb_creator = vb.creator

        items.append(
            HistoryItem(
                id=analysis.id,
                created_at=analysis.created_at.isoformat(),
                status=analysis.status,
                video_a_thumbnail=va_thumb,
                video_a_creator=va_creator,
                video_b_thumbnail=vb_thumb,
                video_b_creator=vb_creator,
            )
        )

    return items
