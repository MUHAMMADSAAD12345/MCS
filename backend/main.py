"""Adaptive Reasoning Agent — FastAPI entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.chat import router as chat_router, set_agent
from api.documents import router as documents_router, set_dependencies
from api.downloads import router as downloads_router
from config import settings
from core.agent import Agent
from core.network_monitor import get_network_monitor
from rag.embedder import EmbeddingEngine
from rag.ingestion import IngestionPipeline
from rag.retriever import RAGRetriever
from rag.vector_store import VectorStore
from services.session_store import init_db
from tools.router import ToolRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Adaptive Reasoning Agent...")

    # ── Startup ───────────────────────────────────────────────────────
    settings.ensure_dirs()
    await init_db()

    # RAG components (may fail if Qdrant not available)
    vector_store = None
    embedder = None
    retriever = None
    ingestion = None

    try:
        vector_store = VectorStore()
        embedder = EmbeddingEngine()
        retriever = RAGRetriever(vector_store, embedder)
        ingestion = IngestionPipeline(vector_store, embedder)
        logger.info("RAG pipeline initialized successfully.")
    except Exception as e:
        logger.warning("RAG pipeline not available: %s (will operate without RAG)", e)

    # Tool router
    tool_router = ToolRouter(rag_retriever=retriever)

    # Agent
    agent = Agent(tool_router=tool_router)
    set_agent(agent)

    # Wire up document endpoints
    set_dependencies(ingestion, vector_store)

    # Start background network probing
    monitor = get_network_monitor()
    monitor.start_background()

    logger.info("Agent ready — serving on %s:%s", settings.APP_HOST, settings.APP_PORT)

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────
    monitor.stop_background()
    logger.info("Agent shut down.")


# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Adaptive Reasoning Agent",
    description="AI chatbot that adapts reasoning depth to network conditions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(downloads_router)


@app.get("/")
async def root():
    return {
        "name": "Adaptive Reasoning Agent",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/api/network/status")
async def network_status():
    """Debug endpoint: current network conditions."""
    monitor = get_network_monitor()
    snapshot = monitor.get_cached_snapshot()
    return snapshot.model_dump()


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    qdrant_ok = False
    try:
        vs = VectorStore()
        qdrant_ok = vs.health_check()
    except Exception:
        pass

    return {
        "status": "healthy",
        "qdrant": "connected" if qdrant_ok else "unavailable",
        "mistral_key_set": bool(settings.MISTRAL_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
