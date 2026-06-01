import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    platform: Mapped[str] = mapped_column(String(20))  # youtube | instagram
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(Text)
    creator: Mapped[str | None] = mapped_column(String(255))
    followers: Mapped[int | None] = mapped_column(Integer)
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    duration: Mapped[float | None] = mapped_column(Float)  # seconds (float from yt-dlp)
    upload_date: Mapped[str | None] = mapped_column(String(20))
    hashtags: Mapped[list | None] = mapped_column(JSON)
    transcript: Mapped[str | None] = mapped_column(Text)
    transcript_segments: Mapped[list | None] = mapped_column(JSON)  # [{start, end, text}]
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    analyses_as_a: Mapped[list["Analysis"]] = relationship(
        "Analysis", foreign_keys="Analysis.video_a_id", back_populates="video_a"
    )
    analyses_as_b: Mapped[list["Analysis"]] = relationship(
        "Analysis", foreign_keys="Analysis.video_b_id", back_populates="video_b"
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    video_a_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("videos.id"), nullable=True)
    video_b_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("videos.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("processing", "complete", "failed", name="analysis_status"),
        default="processing",
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    hook_analysis_a: Mapped[dict | None] = mapped_column(JSON)
    hook_analysis_b: Mapped[dict | None] = mapped_column(JSON)
    structure_a: Mapped[list | None] = mapped_column(JSON)
    structure_b: Mapped[list | None] = mapped_column(JSON)
    viral_patterns_a: Mapped[dict | None] = mapped_column(JSON)
    viral_patterns_b: Mapped[dict | None] = mapped_column(JSON)
    recommendations: Mapped[list | None] = mapped_column(JSON)
    comparison_insights: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    video_a: Mapped["Video"] = relationship("Video", foreign_keys=[video_a_id], back_populates="analyses_as_a")
    video_b: Mapped["Video"] = relationship("Video", foreign_keys=[video_b_id], back_populates="analyses_as_b")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="analysis")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="chat_sessions")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
