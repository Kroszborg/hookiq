import asyncio
import logging
from typing import Any

from app.models.schemas import VideoData
from app.services.gemini import generate_json

logger = logging.getLogger(__name__)


async def _with_retry(coro_fn, label: str, max_retries: int = 3) -> Any:
    """Call an async function with exponential backoff on 429."""
    for attempt in range(max_retries):
        try:
            return await coro_fn()
        except Exception as e:
            err = str(e)
            if "429" in err and attempt < max_retries - 1:
                # Parse retry delay from error message if available
                wait = 65  # default 65s
                import re
                m = re.search(r"retryDelay.*?(\d+)s", err)
                if m:
                    wait = int(m.group(1)) + 5
                logger.info("Rate limited on %s, waiting %ds (attempt %d/%d)", label, wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Max retries exceeded for {label}")


def _first_5s_text(segments: list[dict]) -> str:
    return " ".join(s["text"] for s in segments if s.get("start", 0) <= 5)


async def _analyze_hook(transcript: str, segments: list[dict]) -> dict[str, Any]:
    first_5s = _first_5s_text(segments) or transcript[:300]
    prompt = f"""Analyze the hook of this video content (first 5 seconds).

First 5 seconds: "{first_5s}"
Full transcript (first 500 chars): "{transcript[:500]}"

Score each dimension 1-10 and provide a brief summary.

Return JSON:
{{
  "curiosity_score": <int 1-10>,
  "emotional_score": <int 1-10>,
  "clarity_score": <int 1-10>,
  "retention_potential": <int 1-10>,
  "summary": "<2-3 sentence analysis>"
}}"""
    try:
        return await _with_retry(lambda: generate_json(prompt), "hook_analysis")
    except Exception as e:
        logger.warning("Hook analysis failed: %s", e)
        return {"curiosity_score": 5, "emotional_score": 5, "clarity_score": 5, "retention_potential": 5, "summary": "Analysis unavailable due to rate limits."}


async def _analyze_structure(transcript: str, segments: list[dict], duration: int) -> list[dict[str, Any]]:
    dur = duration or 60
    prompt = f"""Analyze the structure of this video transcript.

Transcript: "{transcript[:2000]}"
Duration: {dur} seconds

Identify 4 segments: Hook, Story, Value, CTA with realistic time ranges.

Return JSON array (exactly 4 items):
[
  {{"segment": "Hook", "start_time": 0.0, "end_time": <float>, "summary": "<what happens>"}},
  {{"segment": "Story", "start_time": <float>, "end_time": <float>, "summary": "<what happens>"}},
  {{"segment": "Value", "start_time": <float>, "end_time": <float>, "summary": "<what happens>"}},
  {{"segment": "CTA", "start_time": <float>, "end_time": {dur}.0, "summary": "<what happens>"}}
]"""
    def _default_segments():
        q = dur / 4
        return [
            {"segment": "Hook", "start_time": 0, "end_time": q, "summary": "Opening hook"},
            {"segment": "Story", "start_time": q, "end_time": q * 2, "summary": "Story buildup"},
            {"segment": "Value", "start_time": q * 2, "end_time": q * 3, "summary": "Value delivery"},
            {"segment": "CTA", "start_time": q * 3, "end_time": dur, "summary": "Call to action"},
        ]

    try:
        result = await _with_retry(lambda: generate_json(prompt), "structure_analysis")
        # Groq sometimes wraps the list in a dict e.g. {"segments": [...]}
        if isinstance(result, list) and len(result) > 0:
            return result
        if isinstance(result, dict):
            for key in ("segments", "structure", "items", "data", "timeline"):
                if key in result and isinstance(result[key], list) and len(result[key]) > 0:
                    return result[key]
        logger.warning("Structure analysis returned unexpected format, using defaults")
        return _default_segments()
    except Exception as e:
        logger.warning("Structure analysis failed: %s", e)
        return _default_segments()


async def _analyze_viral_patterns(transcript: str, metadata: dict) -> dict[str, Any]:
    prompt = f"""Analyze this video for viral psychological patterns.

Transcript: "{transcript[:1500]}"
Engagement rate: {metadata.get('engagement_rate', 'unknown')}%

Detect each pattern and score 1-10. Cite specific evidence from the transcript.

Return JSON:
{{
  "curiosity_gap": {{"present": <bool>, "score": <int>, "evidence": "<quote>"}},
  "open_loop": {{"present": <bool>, "score": <int>, "evidence": "<quote>"}},
  "social_proof": {{"present": <bool>, "score": <int>, "evidence": "<quote>"}},
  "authority": {{"present": <bool>, "score": <int>, "evidence": "<quote>"}},
  "urgency": {{"present": <bool>, "score": <int>, "evidence": "<quote>"}},
  "novelty": {{"present": <bool>, "score": <int>, "evidence": "<quote>"}}
}}"""
    try:
        return await _with_retry(lambda: generate_json(prompt), "viral_patterns")
    except Exception as e:
        logger.warning("Viral patterns failed: %s", e)
        default = {"present": False, "score": 1, "evidence": "Analysis unavailable."}
        return {k: default for k in ["curiosity_gap", "open_loop", "social_proof", "authority", "urgency", "novelty"]}


async def _generate_comparison(video_a: VideoData, video_b: VideoData) -> dict[str, Any]:
    def fmt(v: VideoData, label: str) -> str:
        er = f"{v.engagement_rate:.2f}%" if v.engagement_rate is not None else "N/A (no view count)"
        views = f"{v.views:,}" if v.views is not None else "N/A"
        return (f"Video {label}: {v.creator or 'Unknown'} | {views} views | "
                f"{v.likes or 0:,} likes | {v.comments or 0:,} comments | "
                f"{er} engagement rate")

    # Safe delta calculation — use 0 for missing values but note it
    er_a = video_a.engagement_rate or 0
    er_b = video_b.engagement_rate or 0
    both_have_er = video_a.engagement_rate is not None and video_b.engagement_rate is not None
    delta_note = "" if both_have_er else " (note: one video has no view count, so engagement rate comparison is approximate)"

    prompt = f"""{fmt(video_a, 'A')}
{fmt(video_b, 'B')}

Transcript A (first 600 chars): "{(video_a.transcript or '')[:600]}"
Transcript B (first 600 chars): "{(video_b.transcript or '')[:600]}"

Compare these videos. Which performed better and WHY specifically?
If engagement rate is N/A for a video, base the comparison on likes, comments, and content quality instead.{delta_note}

Return JSON:
{{
  "winner": "<A or B or tie>",
  "performance_delta_pct": <float — absolute difference in engagement rates, or 0 if data unavailable>,
  "hook_comparison": "<2-3 sentences comparing the hooks>",
  "content_comparison": "<2-3 sentences comparing content>",
  "summary": "<2-3 sentence overall analysis>"
}}"""
    try:
        return await _with_retry(lambda: generate_json(prompt), "comparison")
    except Exception as e:
        logger.warning("Comparison failed: %s", e)
        er_a = video_a.engagement_rate or 0
        er_b = video_b.engagement_rate or 0
        _both = video_a.engagement_rate is not None and video_b.engagement_rate is not None
        winner = "A" if er_a > er_b else ("B" if er_b > er_a else "tie")
        return {
            "winner": winner,
            "performance_delta_pct": round(abs(er_a - er_b), 2) if _both else 0.0,
            "hook_comparison": "Hook comparison unavailable — retry later.",
            "content_comparison": "Content comparison unavailable — retry later.",
            "summary": (
                f"Video {winner} had higher engagement ({max(er_a, er_b):.2f}% vs {min(er_a, er_b):.2f}%)."
                if _both else
                f"Video {winner} had more available engagement data."
            ),
        }


async def _generate_recommendations(video_a: VideoData, video_b: VideoData) -> list[dict[str, Any]]:
    prompt = f"""You are a viral content strategist.

Video A (better performer): {video_a.creator} — {f"{video_a.views:,}" if video_a.views else "N/A"} views, {f"{video_a.engagement_rate:.2f}%" if video_a.engagement_rate is not None else "N/A"} engagement
Transcript A (first 800 chars): "{(video_a.transcript or '')[:800]}"

Video B (needs improvement): {video_b.creator} — {f"{video_b.views:,}" if video_b.views else "N/A"} views, {f"{video_b.engagement_rate:.2f}%" if video_b.engagement_rate is not None else "N/A"} engagement
Transcript B (first 800 chars): "{(video_b.transcript or '')[:800]}"

Give 5 specific, actionable improvements for Video B based on what worked in Video A.

Return JSON array (exactly 5 items):
[
  {{"rank": 1, "title": "<short title>", "action": "<specific action>", "evidence_from_a": "<technique from Video A>"}},
  ...
]"""
    try:
        result = await _with_retry(lambda: generate_json(prompt), "recommendations")
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.warning("Recommendations failed: %s", e)
        return [
            {"rank": i + 1, "title": f"Improvement {i + 1}",
             "action": "Analysis unavailable — retry later.",
             "evidence_from_a": "See Video A transcript."}
            for i in range(5)
        ]


async def run_full_analysis(video_a: VideoData, video_b: VideoData) -> dict[str, Any]:
    """
    Run analysis sequentially. Groq free tier allows 30 RPM.
    Each Groq call takes ~2-3s so we don't need artificial sleeps —
    the _with_retry backoff handles any actual 429s.
    """
    seg_a = video_a.transcript_segments or []
    seg_b = video_b.transcript_segments or []
    dur_a = float(video_a.duration or 60)
    dur_b = float(video_b.duration or 60)

    logger.info("Starting intelligence analysis (8 sequential Groq calls)...")

    hook_a = await _analyze_hook(video_a.transcript or "", seg_a)
    hook_b = await _analyze_hook(video_b.transcript or "", seg_b)
    struct_a = await _analyze_structure(video_a.transcript or "", seg_a, dur_a)
    struct_b = await _analyze_structure(video_b.transcript or "", seg_b, dur_b)
    viral_a = await _analyze_viral_patterns(
        video_a.transcript or "",
        {"engagement_rate": video_a.engagement_rate, "views": video_a.views}
    )
    viral_b = await _analyze_viral_patterns(
        video_b.transcript or "",
        {"engagement_rate": video_b.engagement_rate, "views": video_b.views}
    )
    comparison = await _generate_comparison(video_a, video_b)
    recs = await _generate_recommendations(video_a, video_b)

    logger.info("Intelligence analysis complete")

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
