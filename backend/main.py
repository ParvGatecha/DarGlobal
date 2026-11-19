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

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
        "agentic_tools": [
            "search_darglobal_projects",
            "search_wasalt_properties",
            "search_by_location",
            "get_project_details",
            "compare_properties",
            "get_source_information"
        ],
        "status": "OPERATIONAL"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
