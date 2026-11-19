import os
# Optimize memory and thread pool allocation for Render Free Tier (512MB RAM)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.retrieval.hybrid_search import HybridRetriever
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.llm.rag_engine import RAGEngine
from backend.app.agent.tools import AgentToolRegistry
from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.llm.model_selector import model_selector
from backend.app.api.v1 import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DarGlobal Intelligence Backend & Agent Orchestrator...")

    # Initialize Storage Engines
    vector_store = VectorStore(persist_directory=settings.CHROMA_PERSIST_DIRECTORY)
    bm25_store = BM25Store(index_path=settings.BM25_INDEX_PATH)

    # Initialize Ingestion Pipeline
    ingestion_pipeline = IngestionPipeline(vector_store=vector_store, bm25_store=bm25_store)

    # Auto-seed if empty
    if vector_store.get_count() == 0 or bm25_store.get_count() == 0:
        logger.info("Stores are unpopulated. Running initial ingestion pipeline...")
        report = ingestion_pipeline.run(probe_live=False)
        app.state.last_ingestion_report = report
    else:
        logger.info(f"Loaded existing indexed data: ChromaDB={vector_store.get_count()} chunks, BM25={bm25_store.get_count()} docs")

    # Initialize Hybrid Retriever
    retriever = HybridRetriever(vector_store=vector_store, bm25_store=bm25_store)
    
    # Initialize Base RAG Engine (preserved as foundational capability)
    rag_engine = RAGEngine(retriever=retriever)

    # Initialize Agent Tool Registry & Agent Orchestration Layer
    tool_registry = AgentToolRegistry(retriever=retriever)
    agent_orchestrator = AgentOrchestrator(tool_registry=tool_registry, max_steps=5, per_tool_timeout=12.0)

    # Auto-discover best free model
    best_model = model_selector.get_best_model()
    logger.info(f"Active LLM Model selected: {best_model}")

    # Register in application state
    app.state.vector_store = vector_store
    app.state.bm25_store = bm25_store
    app.state.retriever = retriever
    app.state.rag_engine = rag_engine
    app.state.tool_registry = tool_registry
    app.state.agent_orchestrator = agent_orchestrator
    app.state.ingestion_pipeline = ingestion_pipeline

    yield

    logger.info("Shutting down DarGlobal Intelligence Backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Agentic Real Estate Assistant for DarGlobal luxury developments and Wasalt properties.",
    lifespan=lifespan
)

# Production CORS Configuration for Vercel & Cross-Origin SSE
configured_origins = [o for o in settings.CORS_ORIGINS if o != "*"]
if not configured_origins:
    configured_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

cors_kwargs = {
    "allow_origins": configured_origins,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["*"]
}
if settings.CORS_ORIGIN_REGEX:
    cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Mount API Routers at both /api/v1 and root for maximum URL client compatibility
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router)

@app.get("/health", tags=["Health"])
async def root_health():
    """Root health check endpoint for Render service monitoring."""
    vector_store = getattr(app.state, "vector_store", None)
    bm25_store = getattr(app.state, "bm25_store", None)
    v_count = vector_store.get_count() if vector_store else 0
    b_count = bm25_store.get_count() if bm25_store else 0
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "indexed_chunks": v_count,
        "bm25_ready": b_count > 0,
        "agentic_ready": getattr(app.state, "agent_orchestrator", None) is not None
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
        "health_check": "/api/v1/health",
        "agentic_tools": [
            "search_darglobal_projects",
            "search_wasalt_properties",
            "search_by_location",
            "get_project_details",
            "compare_properties",
            "get_source_information",
            "filter_previous_results"
        ],
        "status": "OPERATIONAL"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, workers=1)
