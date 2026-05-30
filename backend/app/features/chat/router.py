import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.features.chat.agent import stream_agent_response
from app.models.db import Analysis, ChatSession, Message, Video
from app.models.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def _video_to_meta(v: Video) -> dict:
    return {
        "id": v.id,
        "platform": v.platform,
        "url": v.url,
        "title": v.title,
        "creator": v.creator,
        "followers": v.followers,
        "views": v.views,
        "likes": v.likes,
        "comments": v.comments,
        "engagement_rate": v.engagement_rate,
        "duration": v.duration,
        "upload_date": v.upload_date,
    }


@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    result = await db.execute(select(Analysis).where(Analysis.id == request.analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.status != "complete":
        raise HTTPException(status_code=400, detail=f"Analysis not ready (status: {analysis.status})")

    res_a = await db.execute(select(Video).where(Video.id == analysis.video_a_id))
    video_a = res_a.scalar_one_or_none()
    res_b = await db.execute(select(Video).where(Video.id == analysis.video_b_id))
    video_b = res_b.scalar_one_or_none()

    if not video_a or not video_b:
        raise HTTPException(status_code=500, detail="Video data missing")

    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        session = ChatSession(id=session_id, analysis_id=request.analysis_id)
        db.add(session)
        await db.commit()

    user_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    video_a_meta = _video_to_meta(video_a)
    video_b_meta = _video_to_meta(video_b)

    async def event_generator():
        full_text = ""
        final_citations = []
        yield f"data: {json.dumps({'session_id': session_id, 'text': '', 'done': False})}\n\n"

        try:
            async for chunk, citations in stream_agent_response(
                analysis_id=request.analysis_id,
                session_id=session_id,
                message=request.message,
                video_a_meta=video_a_meta,
                video_b_meta=video_b_meta,
            ):
                if chunk:
                    full_text += chunk
                    yield f"data: {json.dumps({'text': chunk, 'done': False})}\n\n"
                if citations:
                    final_citations = citations

            ai_msg = Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=full_text,
                citations=final_citations,
            )
            async with async_session_maker() as save_db:
                save_db.add(ai_msg)
                await save_db.commit()

            yield f"data: {json.dumps({'text': '', 'citations': final_citations, 'done': True})}\n\n"

        except Exception as e:
            logger.exception("Chat streaming error: %s", e)
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
