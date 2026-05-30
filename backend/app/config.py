from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    GEMINI_API_KEY: str = ""
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "video_chunks"
    BGE_MODEL: str = "BAAI/bge-small-en-v1.5"
    DATABASE_URL: str = "sqlite+aiosqlite:///./hookiq.db"
    FRONTEND_URL: str = "http://localhost:3000"
    WHISPER_MODEL: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
