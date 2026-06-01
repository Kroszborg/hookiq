"""Singleton Whisper model — load once, reuse everywhere."""
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_whisper_model():
    from faster_whisper import WhisperModel
    from app.config import get_settings
    settings = get_settings()
    logger.info("Loading Whisper model: %s (device=%s)", settings.WHISPER_MODEL, settings.WHISPER_DEVICE)
    model = WhisperModel(settings.WHISPER_MODEL, device=settings.WHISPER_DEVICE, compute_type=settings.WHISPER_COMPUTE_TYPE)
    logger.info("Whisper model ready")
    return model


def transcribe(audio_path: str) -> tuple[str, list[dict]]:
    model = get_whisper_model()
    segments, _ = model.transcribe(audio_path, beam_size=5)
    segs = list(segments)
    full_text = " ".join(s.text.strip() for s in segs)
    seg_dicts = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]
    return full_text, seg_dicts
