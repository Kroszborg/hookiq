import hashlib
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from app.models.schemas import VideoData

logger = logging.getLogger(__name__)


def _extract_shortcode(url: str) -> str | None:
    match = re.search(r"/(?:reel|p)/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def _get_ytdlp_metadata(url: str) -> dict:
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", "--skip-download", url],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        logger.warning("yt-dlp instagram metadata failed: %s", e)
    return {}


def _get_follower_count(username: str) -> int | None:
    try:
        import instaloader
        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, username)
        return profile.followers
    except Exception as e:
        logger.warning("instaloader followers failed for %s: %s", username, e)
        return None


def _download_audio_ytdlp(url: str, output_path: str) -> bool:
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "5",
                "--no-playlist",
                "-o", output_path,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning("yt-dlp audio download failed: %s", e)
        return False


def _transcribe_with_whisper(audio_path: str) -> tuple[str, list[dict]]:
    from faster_whisper import WhisperModel
    from app.config import get_settings
    settings = get_settings()
    model = WhisperModel(settings.WHISPER_MODEL, device=settings.WHISPER_DEVICE, compute_type=settings.WHISPER_COMPUTE_TYPE)
    segments, _ = model.transcribe(audio_path, beam_size=5)
    segments_list = list(segments)
    full_text = " ".join(s.text.strip() for s in segments_list)
    seg_dicts = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments_list]
    return full_text, seg_dicts


async def extract_instagram(url: str) -> VideoData:
    url_hash = hashlib.sha256(url.strip().encode()).hexdigest()
    meta = _get_ytdlp_metadata(url)

    uploader = meta.get("uploader") or meta.get("uploader_id") or ""
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

    hashtags = meta.get("tags", []) or []
    description = meta.get("description") or meta.get("title") or ""
    tag_matches = re.findall(r"#(\w+)", description)
    if tag_matches:
        hashtags = list(set(hashtags + tag_matches))

    thumbnail = meta.get("thumbnail") or (meta.get("thumbnails") or [{}])[-1].get("url")
    duration = meta.get("duration")

    followers = meta.get("channel_follower_count")
    if not followers and uploader:
        clean_username = uploader.lstrip("@")
        followers = _get_follower_count(clean_username)

    transcript_text = None
    transcript_segments: list[dict] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = str(Path(tmpdir) / "audio.mp3")
        if _download_audio_ytdlp(url, audio_path) and Path(audio_path).exists():
            transcript_text, transcript_segments = _transcribe_with_whisper(audio_path)
            logger.info("Got Instagram transcript via Whisper for %s", url)
        else:
            logger.warning("Could not download audio for %s", url)
            transcript_text = description or "Transcript unavailable."

    return VideoData(
        platform="instagram",
        url=url,
        url_hash=url_hash,
        title=meta.get("title") or description[:100] if description else None,
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
