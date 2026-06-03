import asyncio
import hashlib
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from app.models.schemas import VideoData

logger = logging.getLogger(__name__)


def _cookies_file() -> list[str]:
    """Return --cookies flag if a cookies file exists (enables authenticated Instagram scraping)."""
    import os
    paths = [
        "/app/instagram_cookies.txt",           # Docker container path
        os.path.expanduser("~/instagram_cookies.txt"),  # VM home dir
    ]
    for p in paths:
        if os.path.exists(p):
            logger.info("Using Instagram cookies from %s", p)
            return ["--cookies", p]
    return []


def _get_ytdlp_metadata(url: str) -> dict:
    try:
        cmd = ["yt-dlp", "--dump-json", "--no-playlist", "--skip-download"] + _cookies_file() + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        logger.warning("yt-dlp instagram metadata failed: %s", e)
    return {}


def _get_follower_count_sync(username: str) -> int | None:
    """Fetch follower count via instaloader — runs in thread pool to avoid blocking."""
    try:
        import instaloader
        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, username.lstrip("@"))
        return profile.followers
    except Exception as e:
        logger.warning("instaloader followers failed for %s: %s", username, e)
        return None


def _download_audio_ytdlp(url: str, output_path: str) -> bool:
    try:
        cmd = ["yt-dlp", "--extract-audio", "--audio-format", "mp3",
               "--audio-quality", "5", "--no-playlist"] + _cookies_file() + ["-o", output_path, url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        logger.warning("yt-dlp audio download failed: %s", e)
        return False


def _transcribe_with_whisper(audio_path: str) -> tuple[str, list[dict]]:
    from app.services.whisper import transcribe
    return transcribe(audio_path)


def _extract_instagram_sync(url: str) -> VideoData:
    """Synchronous extraction — called via asyncio.to_thread so it never blocks the event loop."""
    url_hash = hashlib.sha256(url.strip().encode()).hexdigest()
    meta = _get_ytdlp_metadata(url)

    uploader = meta.get("uploader") or meta.get("uploader_id") or ""
    views = meta.get("view_count")
    likes = meta.get("like_count")
    comments = meta.get("comment_count")

    # Prefer view-based ER; fall back to follower-based ER (standard Instagram metric)
    engagement_rate = None
    interactions = (likes or 0) + (comments or 0)
    if views and views > 0 and interactions:
        engagement_rate = round(interactions / views * 100, 4)

    upload_date_raw = meta.get("upload_date", "")
    upload_date = None
    if upload_date_raw and len(upload_date_raw) == 8:
        upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:]}"

    description = meta.get("description") or meta.get("title") or ""
    hashtags = list(meta.get("tags", []) or [])
    tag_matches = re.findall(r"#(\w+)", description)
    if tag_matches:
        hashtags = list(set(hashtags + tag_matches))

    thumbnail = meta.get("thumbnail") or (meta.get("thumbnails") or [{}])[-1].get("url")
    duration = meta.get("duration")  # float OK — schema accepts float

    # Follower count: try yt-dlp first (fast), then instaloader (slow but more reliable)
    followers = (
        meta.get("channel_follower_count")
        or meta.get("uploader_follower_count")
        or meta.get("uploader_id_follower_count")
    )
    if not followers and uploader:
        followers = _get_follower_count_sync(uploader)

    # If no view-based ER, compute follower-based ER (standard Instagram KPI when views unavailable)
    if engagement_rate is None and followers and followers > 0 and interactions:
        engagement_rate = round(interactions / followers * 100, 4)
        logger.info("Using follower-based ER for %s: %.2f%%", uploader, engagement_rate)

    # Transcript via Whisper
    transcript_text: str | None = None
    transcript_segments: list[dict] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = str(Path(tmpdir) / "audio.mp3")
        if _download_audio_ytdlp(url, audio_path) and Path(audio_path).exists():
            transcript_text, transcript_segments = _transcribe_with_whisper(audio_path)
            logger.info("Got Instagram transcript via Whisper for %s", url)
        else:
            logger.warning("Could not download Instagram audio for %s, using description", url)
            transcript_text = description or "Transcript unavailable for this reel."

    return VideoData(
        platform="instagram",
        url=url,
        url_hash=url_hash,
        title=meta.get("title") or (description[:100] if description else None),
        creator=uploader,
        followers=followers,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=engagement_rate,
        duration=duration,
        upload_date=upload_date,
        hashtags=hashtags[:20],
        transcript=transcript_text,
        transcript_segments=transcript_segments,
        thumbnail_url=thumbnail,
    )


async def extract_instagram(url: str) -> VideoData:
    """Non-blocking wrapper — runs heavy sync work in thread pool."""
    return await asyncio.to_thread(_extract_instagram_sync, url)
