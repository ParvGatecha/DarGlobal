from fastapi import APIRouter
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.properties import router as properties_router
from backend.app.api.v1.ingest import router as ingest_router
from backend.app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["Chat & RAG"])
api_router.include_router(properties_router, prefix="/properties", tags=["Properties"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["Ingestion"])
api_router.include_router(health_router, prefix="/health", tags=["Health & Status"])
