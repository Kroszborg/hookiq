from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Ingestion ──────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Start processing two video URLs."""
    video_a_url: str = Field(..., description="YouTube or Instagram URL for Video A")
    video_b_url: str = Field(..., description="YouTube or Instagram URL for Video B")

    model_config = {"json_schema_extra": {"example": {
        "video_a_url": "https://www.youtube.com/shorts/abc123",
        "video_b_url": "https://www.instagram.com/reel/xyz456/",
    }}}


class AnalyzeResponse(BaseModel):
    """Returned immediately — use analysis_id to poll progress and results."""
    analysis_id: str = Field(..., description="UUID to track this analysis")


class VideoData(BaseModel):
    """Internal: extracted video data from YouTube or Instagram."""
    platform: str
    url: str
    url_hash: str
    title: str | None = None
    creator: str | None = None
    followers: int | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    engagement_rate: float | None = None
    duration: int | None = None
    upload_date: str | None = None
    hashtags: list[str] = []
    transcript: str | None = None
    transcript_segments: list[dict[str, Any]] = []
    thumbnail_url: str | None = None


class VideoCardResponse(BaseModel):
    """Video metadata returned in the analysis dashboard."""
    id: str
    platform: Literal["youtube", "instagram"]
    url: str
    title: str | None
    creator: str | None
    followers: int | None
    views: int | None
    likes: int | None
    comments: int | None
    engagement_rate: float | None = Field(None, description="(likes + comments) / views * 100")
    duration: int | None = Field(None, description="Duration in seconds")
    upload_date: str | None
    hashtags: list[str]
    thumbnail_url: str | None


# ── Intelligence Layer ─────────────────────────────────────────────────────

class HookAnalysis(BaseModel):
    """Scores for the first 5 seconds of a video, each 1–10."""
    curiosity_score: int = Field(..., ge=1, le=10)
    emotional_score: int = Field(..., ge=1, le=10)
    clarity_score: int = Field(..., ge=1, le=10)
    retention_potential: int = Field(..., ge=1, le=10)
    summary: str


class StructureSegment(BaseModel):
    """One content segment identified by the AI (Hook, Story, Value, or CTA)."""
    segment: Literal["Hook", "Story", "Value", "CTA"]
    start_time: float = Field(..., description="Seconds from video start")
    end_time: float
    summary: str


class ViralPattern(BaseModel):
    """Whether a viral pattern is present in the video."""
    present: bool
    score: int = Field(..., ge=1, le=10)
    evidence: str = Field(..., description="Specific quote or technique from the transcript")


class ViralPatterns(BaseModel):
    """Six viral psychological patterns detected in a video."""
    curiosity_gap: ViralPattern
    open_loop: ViralPattern
    social_proof: ViralPattern
    authority: ViralPattern
    urgency: ViralPattern
    novelty: ViralPattern


class Recommendation(BaseModel):
    """One improvement recommendation for Video B based on Video A."""
    rank: int
    title: str
    action: str
    evidence_from_a: str = Field(..., description="Specific technique from Video A that supports this recommendation")


class ComparisonInsights(BaseModel):
    """AI-generated comparison between Video A and Video B."""
    winner: Literal["A", "B", "tie"]
    performance_delta_pct: float = Field(..., description="Absolute difference in engagement rates")
    hook_comparison: str
    content_comparison: str
    summary: str


# ── Full Analysis Response ─────────────────────────────────────────────────

class AnalysisResponse(BaseModel):
    """Complete analysis result with video cards and all AI insights."""
    id: str
    status: Literal["processing", "complete", "failed"]
    video_a: VideoCardResponse | None = None
    video_b: VideoCardResponse | None = None
    hook_analysis_a: HookAnalysis | None = None
    hook_analysis_b: HookAnalysis | None = None
    structure_a: list[StructureSegment] | None = None
    structure_b: list[StructureSegment] | None = None
    viral_patterns_a: ViralPatterns | None = None
    viral_patterns_b: ViralPatterns | None = None
    recommendations: list[Recommendation] | None = None
    comparison_insights: ComparisonInsights | None = None
    error_message: str | None = None


# ── Chat ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Send a message to the RAG agent."""
    analysis_id: str = Field(..., description="UUID from /analyze response")
    message: str = Field(..., description="Natural language question about the videos")
    session_id: str | None = Field(None, description="Reuse existing session to maintain memory; omit for new session")

    model_config = {"json_schema_extra": {"example": {
        "analysis_id": "7cd8ef43-6f3b-41ae-9008-7826eb3e8e5b",
        "message": "Why did Video A outperform Video B?",
        "session_id": None,
    }}}


class Citation(BaseModel):
    """Source chunk cited in an AI response."""
    tag: str = Field(..., description="e.g. A-Chunk-3 or B-Chunk-7")
    label: Literal["A", "B"]
    chunk_id: int
    score: float = Field(..., description="Cosine similarity score from vector search")


class ChatChunk(BaseModel):
    """One SSE event from the /chat stream."""
    session_id: str | None = None
    text: str = Field(default="", description="Token chunk to append to the response")
    citations: list[Citation] = Field(default_factory=list, description="Populated in the final done=true event")
    done: bool = False
    error: str | None = None


# ── Progress SSE ──────────────────────────────────────────────────────────

class ProgressEvent(BaseModel):
    """One SSE event from /analyze/progress/{id}."""
    step: str = Field(..., description="Human-readable pipeline step name")
    index: int
    total: int
    done: bool
    error: str | None = None
    heartbeat: bool | None = None


# ── History ───────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    """Summary of a past analysis for the history list."""
    id: str
    created_at: str
    status: Literal["processing", "complete", "failed"]
    video_a_thumbnail: str | None
    video_a_creator: str | None
    video_b_thumbnail: str | None
    video_b_creator: str | None
