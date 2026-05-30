from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM — set LLM_PROVIDER=groq (default) or gemini
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "video_chunks"

    # Embeddings
    BGE_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./hookiq.db"

    # Server
    FRONTEND_URL: str = "*"

    # Whisper (Instagram transcription)
    WHISPER_MODEL: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
