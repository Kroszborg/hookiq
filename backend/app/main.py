import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.features.ingestion.router import router as ingestion_router
from app.features.chat.router import router as chat_router
from app.features.history.router import router as history_router
from app.services.embeddings import get_embedding_model
from app.services.qdrant import ensure_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Initializing HookIQ backend...")
    await init_db()
    logger.info("Database initialized")
    get_embedding_model()
    logger.info("Embedding model loaded")
    try:
        ensure_collection()
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning("Qdrant not available at startup: %s", e)
    logger.info("HookIQ backend ready")
    yield
    logger.info("Shutting down HookIQ backend")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HookIQ API",
        description="AI-powered YouTube vs Instagram Reels comparison engine",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
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
