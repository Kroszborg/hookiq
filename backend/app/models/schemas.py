from __future__ import annotations

from typing import Any

from pydantic import BaseModel, HttpUrl


class AnalyzeRequest(BaseModel):
    video_a_url: str
    video_b_url: str


class AnalyzeResponse(BaseModel):
    analysis_id: str


class VideoData(BaseModel):
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
    id: str
    platform: str
    url: str
    title: str | None
    creator: str | None
    followers: int | None
    views: int | None
    likes: int | None
    comments: int | None
    engagement_rate: float | None
    duration: int | None
    upload_date: str | None
    hashtags: list[str]
    thumbnail_url: str | None


class HookAnalysis(BaseModel):
    curiosity_score: int
    emotional_score: int
    clarity_score: int
    retention_potential: int
    summary: str


class StructureSegment(BaseModel):
    segment: str  # Hook | Story | Value | CTA
    start_time: float
    end_time: float
    summary: str


class ViralPattern(BaseModel):
    present: bool
    score: int
    evidence: str


class ViralPatterns(BaseModel):
    curiosity_gap: ViralPattern
    open_loop: ViralPattern
    social_proof: ViralPattern
    authority: ViralPattern
    urgency: ViralPattern
    novelty: ViralPattern


class Recommendation(BaseModel):
    rank: int
    title: str
    action: str
    evidence_from_a: str


class ComparisonInsights(BaseModel):
    winner: str  # "A" | "B" | "tie"
    performance_delta_pct: float
    hook_comparison: str
    content_comparison: str
    summary: str


class AnalysisResponse(BaseModel):
    id: str
    status: str
    video_a: VideoCardResponse | None = None
    video_b: VideoCardResponse | None = None
    hook_analysis_a: dict | None = None
    hook_analysis_b: dict | None = None
    structure_a: list[dict] | None = None
    structure_b: list[dict] | None = None
    viral_patterns_a: dict | None = None
    viral_patterns_b: dict | None = None
    recommendations: list[dict] | None = None
    comparison_insights: dict | None = None
    error_message: str | None = None


class ChatRequest(BaseModel):
    analysis_id: str
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    text: str
    citations: list[dict]


class ProgressEvent(BaseModel):
    step: str
    index: int
    total: int
    done: bool
    error: str | None = None


class HistoryItem(BaseModel):
    id: str
    created_at: str
    status: str
    video_a_thumbnail: str | None
    video_a_creator: str | None
    video_b_thumbnail: str | None
    video_b_creator: str | None
