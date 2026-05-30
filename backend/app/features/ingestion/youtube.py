import hashlib
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

from app.models.schemas import VideoData

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str | None:
    import re
    patterns = [
        r"(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be\/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _get_ytdlp_metadata(url: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", "--skip-download", url],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        logger.warning("yt-dlp metadata failed: %s", e)
    return {}


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


async def extract_youtube(url: str) -> VideoData:
    url_hash = hashlib.sha256(url.strip().encode()).hexdigest()
    meta = _get_ytdlp_metadata(url)

    followers = meta.get("channel_follower_count") or meta.get("uploader_subscriber_count")
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
    thumbnail = meta.get("thumbnail") or (meta.get("thumbnails") or [{}])[-1].get("url")

    transcript_text = None
    transcript_segments: list[dict] = []

    video_id = _extract_video_id(url)
    if video_id:
        try:
            raw_segments = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join(s["text"] for s in raw_segments)
            transcript_segments = [
                {"start": s["start"], "end": s["start"] + s.get("duration", 0), "text": s["text"]}
                for s in raw_segments
            ]
            logger.info("Got YouTube transcript via API for %s", video_id)
        except (NoTranscriptFound, TranscriptsDisabled):
            logger.info("No transcript via API for %s, falling back to Whisper", video_id)
        except Exception as e:
            logger.warning("Transcript API error: %s", e)

    if not transcript_text:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = str(Path(tmpdir) / "audio.mp3")
            if _download_audio_ytdlp(url, audio_path) and Path(audio_path).exists():
                transcript_text, transcript_segments = _transcribe_with_whisper(audio_path)
                logger.info("Got YouTube transcript via Whisper for %s", url)

    return VideoData(
        platform="youtube",
        url=url,
        url_hash=url_hash,
        title=meta.get("title"),
        creator=meta.get("uploader") or meta.get("channel"),
        followers=followers,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=engagement_rate,
        duration=meta.get("duration"),
        upload_date=upload_date,
        hashtags=hashtags[:20],
        transcript=transcript_text,
        transcript_segments=transcript_segments,
        thumbnail_url=thumbnail,
    )
