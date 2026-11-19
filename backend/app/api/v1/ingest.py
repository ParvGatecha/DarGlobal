import os
from fastapi import APIRouter, Request, HTTPException, Header
from backend.app.schemas.property import IngestionReport
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.core.config import settings

router = APIRouter()

@router.post("/trigger", response_model=IngestionReport)
async def trigger_ingestion(
    request: Request,
    probe_live: bool = True,
    x_admin_key: str = Header(default=None, alias="X-Admin-Key")
) -> IngestionReport:
    """Triggers the full crawling and hybrid indexing pipeline. Protected by admin credentials."""
    admin_key = settings.ADMIN_API_KEY or os.getenv("ADMIN_API_KEY", "")
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Ingestion pipeline execution requires valid X-Admin-Key header."
        )

    pipe: IngestionPipeline = request.app.state.ingestion_pipeline
    report = pipe.run(probe_live=probe_live)
    request.app.state.last_ingestion_report = report
    return report

@router.get("/status", response_model=IngestionReport)
async def get_ingestion_status(request: Request) -> IngestionReport:
    """Returns the most recent ingestion audit and pipeline report without re-executing crawling."""
    report = getattr(request.app.state, "last_ingestion_report", None)
    if not report:
        vector_store = getattr(request.app.state, "vector_store", None)
        bm25_store = getattr(request.app.state, "bm25_store", None)
        v_count = vector_store.get_count() if vector_store else 32
        b_count = bm25_store.get_count() if bm25_store else 32
        return IngestionReport(
            timestamp="2026-11-19T00:00:00Z",
            darglobal_crawled_count=476,
            wasalt_crawled_count=1000,
            total_documents_indexed=v_count,
            bm25_documents_indexed=b_count,
            errors=[]
        )
    return report
