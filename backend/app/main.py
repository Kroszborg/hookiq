import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.features.chat.router import router as chat_router
from app.features.history.router import router as history_router
from app.features.ingestion.router import router as ingestion_router
from app.services.embeddings import get_embedding_model
from app.services.qdrant import ensure_collection
from app.services.whisper import get_whisper_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def _wait_for_qdrant(retries: int = 10, delay: float = 3.0) -> None:
    from qdrant_client import QdrantClient
    from app.config import get_settings
    settings = get_settings()
    for i in range(retries):
        try:
            client = QdrantClient(url=settings.QDRANT_URL, timeout=5)
            client.get_collections()
            logger.info("Qdrant is ready")
            return
        except Exception as e:
            logger.info("Waiting for Qdrant (%d/%d): %s", i + 1, retries, e)
            await asyncio.sleep(delay)
    logger.warning("Qdrant not reachable after %d retries — continuing anyway", retries)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HookIQ backend...")

    # Ensure data directory exists
    os.makedirs("/app/data", exist_ok=True)

    await init_db()
    logger.info("Database ready")

    get_embedding_model()
    logger.info("Embedding model loaded")
    get_whisper_model()
    logger.info("Whisper model loaded")

    await _wait_for_qdrant()
    try:
        ensure_collection()
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning("Qdrant collection setup deferred: %s", e)

    logger.info("HookIQ backend ready — listening on :8000")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="HookIQ API",
        description="AI video comparison engine — YouTube Shorts + Instagram Reels",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Allow all origins — tighten in production via FRONTEND_URL env var
    settings = get_settings()
    frontend_url = settings.FRONTEND_URL

    origins = ["*"] if frontend_url == "*" else [
        frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=frontend_url != "*",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingestion_router)
    app.include_router(chat_router)
    app.include_router(history_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "hookiq"}

    return app


app = create_app()
