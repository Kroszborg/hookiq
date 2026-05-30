import asyncio
import logging
from typing import Any

from app.models.schemas import VideoData
from app.services.gemini import generate_json

logger = logging.getLogger(__name__)


def _first_5s_text(segments: list[dict]) -> str:
    texts = [s["text"] for s in segments if s.get("start", 0) <= 5]
    return " ".join(texts) if texts else ""


async def _analyze_hook(transcript: str, segments: list[dict]) -> dict[str, Any]:
    first_5s = _first_5s_text(segments) or transcript[:300]
    prompt = f"""Analyze the hook of this video content (first 5 seconds).

First 5 seconds transcript: "{first_5s}"

Full transcript context (first 500 chars): "{transcript[:500]}"

Score each dimension 1-10 and provide a brief summary of what makes this hook effective or weak.

Return JSON with exactly these fields:
{{
  "curiosity_score": <int 1-10>,
  "emotional_score": <int 1-10>,
  "clarity_score": <int 1-10>,
  "retention_potential": <int 1-10>,
  "summary": "<2-3 sentence analysis>"
}}"""
    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.warning("Hook analysis failed: %s", e)
        return {"curiosity_score": 5, "emotional_score": 5, "clarity_score": 5, "retention_potential": 5, "summary": "Analysis unavailable."}


async def _analyze_structure(transcript: str, segments: list[dict], duration: int) -> list[dict[str, Any]]:
    dur = duration or 60
    prompt = f"""Analyze the structure of this video transcript.

Transcript: "{transcript[:2000]}"
Video duration: {dur} seconds

Identify the 4 structural segments: Hook, Story, Value, CTA.
Estimate realistic time ranges based on typical short-form video structure.

Return JSON array with exactly 4 objects:
[
  {{"segment": "Hook", "start_time": 0.0, "end_time": <float>, "summary": "<what happens>"}},
  {{"segment": "Story", "start_time": <float>, "end_time": <float>, "summary": "<what happens>"}},
  {{"segment": "Value", "start_time": <float>, "end_time": <float>, "summary": "<what happens>"}},
  {{"segment": "CTA", "start_time": <float>, "end_time": {dur}.0, "summary": "<what happens>"}}
]"""
    try:
        result = await generate_json(prompt)
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        logger.warning("Structure analysis failed: %s", e)
        quarter = dur / 4
        return [
            {"segment": "Hook", "start_time": 0, "end_time": quarter, "summary": "Opening hook"},
            {"segment": "Story", "start_time": quarter, "end_time": quarter * 2, "summary": "Story buildup"},
            {"segment": "Value", "start_time": quarter * 2, "end_time": quarter * 3, "summary": "Value delivery"},
            {"segment": "CTA", "start_time": quarter * 3, "end_time": dur, "summary": "Call to action"},
        ]


async def _analyze_viral_patterns(transcript: str, metadata: dict) -> dict[str, Any]:
    prompt = f"""Analyze this video content for viral psychological patterns.

Transcript: "{transcript[:1500]}"
Engagement rate: {metadata.get('engagement_rate', 'unknown')}%
Views: {metadata.get('views', 'unknown')}

For each pattern, determine if it's present, score its strength (1-10), and cite specific evidence from the transcript.

Return JSON:
{{
  "curiosity_gap": {{"present": <bool>, "score": <int 1-10>, "evidence": "<quote or example>"}},
  "open_loop": {{"present": <bool>, "score": <int 1-10>, "evidence": "<quote or example>"}},
  "social_proof": {{"present": <bool>, "score": <int 1-10>, "evidence": "<quote or example>"}},
  "authority": {{"present": <bool>, "score": <int 1-10>, "evidence": "<quote or example>"}},
  "urgency": {{"present": <bool>, "score": <int 1-10>, "evidence": "<quote or example>"}},
  "novelty": {{"present": <bool>, "score": <int 1-10>, "evidence": "<quote or example>"}}
}}"""
    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.warning("Viral patterns analysis failed: %s", e)
        default = {"present": False, "score": 1, "evidence": "Analysis unavailable."}
        return {k: default for k in ["curiosity_gap", "open_loop", "social_proof", "authority", "urgency", "novelty"]}


async def _generate_comparison(video_a: VideoData, video_b: VideoData) -> dict[str, Any]:
    def meta_summary(v: VideoData, label: str) -> str:
        return (
            f"Video {label}: {v.creator} | {v.views or 0:,} views | "
            f"{v.likes or 0:,} likes | {v.comments or 0:,} comments | "
            f"{v.engagement_rate or 0:.2f}% engagement | {v.followers or 0:,} followers"
        )

    prompt = f"""{meta_summary(video_a, 'A')}
{meta_summary(video_b, 'B')}

Transcript A (first 800 chars): "{(video_a.transcript or '')[:800]}"
Transcript B (first 800 chars): "{(video_b.transcript or '')[:800]}"

Compare these two videos and determine which performed better. Be specific about WHY.

Return JSON:
{{
  "winner": "<A or B or tie>",
  "performance_delta_pct": <float, percentage difference in engagement rates>,
  "hook_comparison": "<2-3 sentences comparing the hooks>",
  "content_comparison": "<2-3 sentences comparing content structure and delivery>",
  "summary": "<2-3 sentence overall winner analysis>"
}}"""
    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.warning("Comparison failed: %s", e)
        er_a = video_a.engagement_rate or 0
        er_b = video_b.engagement_rate or 0
        winner = "A" if er_a > er_b else ("B" if er_b > er_a else "tie")
        delta = abs(er_a - er_b)
        return {
            "winner": winner,
            "performance_delta_pct": round(delta, 2),
            "hook_comparison": "Could not analyze hook comparison.",
            "content_comparison": "Could not analyze content comparison.",
            "summary": f"Video {winner} had higher engagement rate.",
        }


async def _generate_recommendations(video_a: VideoData, video_b: VideoData) -> list[dict[str, Any]]:
    prompt = f"""You are a viral content strategist.

Video A (better performer): {video_a.creator} — {video_a.views or 0:,} views, {video_a.engagement_rate or 0:.2f}% engagement
Transcript A (first 1000 chars): "{(video_a.transcript or '')[:1000]}"

Video B (needs improvement): {video_b.creator} — {video_b.views or 0:,} views, {video_b.engagement_rate or 0:.2f}% engagement
Transcript B (first 1000 chars): "{(video_b.transcript or '')[:1000]}"

Generate exactly 5 specific, actionable improvements for Video B based on what worked in Video A.
Reference specific techniques from Video A with evidence.

Return JSON array:
[
  {{
    "rank": 1,
    "title": "<short improvement title>",
    "action": "<specific action to take>",
    "evidence_from_a": "<specific quote or technique from Video A that works>"
  }},
  ... (5 total)
]"""
    try:
        result = await generate_json(prompt)
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        logger.warning("Recommendations failed: %s", e)
        return [
            {
                "rank": i + 1,
                "title": f"Improvement {i + 1}",
                "action": "Review Video A for specific techniques.",
                "evidence_from_a": "See Video A transcript.",
            }
            for i in range(5)
        ]


async def run_full_analysis(video_a: VideoData, video_b: VideoData) -> dict[str, Any]:
    seg_a = video_a.transcript_segments or []
    seg_b = video_b.transcript_segments or []
    dur_a = video_a.duration or 60
    dur_b = video_b.duration or 60

    (hook_a, hook_b, struct_a, struct_b, viral_a, viral_b, comparison, recs) = await asyncio.gather(
        _analyze_hook(video_a.transcript or "", seg_a),
        _analyze_hook(video_b.transcript or "", seg_b),
        _analyze_structure(video_a.transcript or "", seg_a, dur_a),
        _analyze_structure(video_b.transcript or "", seg_b, dur_b),
        _analyze_viral_patterns(video_a.transcript or "", {"engagement_rate": video_a.engagement_rate, "views": video_a.views}),
        _analyze_viral_patterns(video_b.transcript or "", {"engagement_rate": video_b.engagement_rate, "views": video_b.views}),
        _generate_comparison(video_a, video_b),
        _generate_recommendations(video_a, video_b),
    )

    return {
        "hook_a": hook_a,
        "hook_b": hook_b,
        "structure_a": struct_a,
        "structure_b": struct_b,
        "viral_a": viral_a,
        "viral_b": viral_b,
        "comparison": comparison,
        "recommendations": recs,
    }
