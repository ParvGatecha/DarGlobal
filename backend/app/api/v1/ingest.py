from fastapi import APIRouter, Request
from backend.app.schemas.property import IngestionReport
from backend.app.ingestion.pipeline import IngestionPipeline

router = APIRouter()

@router.post("/trigger", response_model=IngestionReport)
async def trigger_ingestion(
    request: Request,
    probe_live: bool = True,
) -> IngestionReport:
    """Triggers the full crawling and hybrid indexing pipeline."""
    pipe: IngestionPipeline = request.app.state.ingestion_pipeline
    report = pipe.run(probe_live=probe_live)
    request.app.state.last_ingestion_report = report
    return report

@router.get("/status", response_model=IngestionReport)
async def get_ingestion_status(request: Request) -> IngestionReport:
    """Returns the most recent ingestion audit and pipeline report."""
    report = getattr(request.app.state, "last_ingestion_report", None)
    if not report:
        pipe: IngestionPipeline = request.app.state.ingestion_pipeline
        report = pipe.run(probe_live=False)
        request.app.state.last_ingestion_report = report
    return report
