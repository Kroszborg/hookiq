"""TikTok extractor — yt-dlp handles TikTok natively."""
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


def _get_ytdlp_metadata(url: str) -> dict:
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", "--skip-download", url],
            capture_output=True, text=True, timeout=90,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        logger.warning("yt-dlp TikTok metadata failed: %s", e)
    return {}


def _download_audio(url: str, output_path: str) -> bool:
    try:
        result = subprocess.run(
            ["yt-dlp", "--extract-audio", "--audio-format", "mp3",
             "--audio-quality", "5", "--no-playlist", "-o", output_path, url],
            capture_output=True, text=True, timeout=300,
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning("yt-dlp TikTok audio failed: %s", e)
        return False


def _extract_tiktok_sync(url: str) -> VideoData:
    url_hash = hashlib.sha256(url.strip().encode()).hexdigest()
    meta = _get_ytdlp_metadata(url)

    uploader = meta.get("uploader") or meta.get("creator") or meta.get("uploader_id") or ""
    views = meta.get("view_count")
    likes = meta.get("like_count")
    comments = meta.get("comment_count")

    engagement_rate = None
    if views and views > 0 and (likes is not None or comments is not None):
        engagement_rate = round(((likes or 0) + (comments or 0)) / views * 100, 4)

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
    duration = meta.get("duration")
    followers = meta.get("channel_follower_count") or meta.get("uploader_follower_count")

    transcript_text: str | None = None
    transcript_segments: list[dict] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = str(Path(tmpdir) / "audio.mp3")
        if _download_audio(url, audio_path) and Path(audio_path).exists():
            from app.services.whisper import transcribe
            transcript_text, transcript_segments = transcribe(audio_path)
            logger.info("Got TikTok transcript via Whisper for %s", url)
        else:
            transcript_text = description or "Transcript unavailable."

    return VideoData(
        platform="tiktok",
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


async def extract_tiktok(url: str) -> VideoData:
    """Non-blocking wrapper."""
    return await asyncio.to_thread(_extract_tiktok_sync, url)
