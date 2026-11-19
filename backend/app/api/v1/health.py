from fastapi import APIRouter, Request
from backend.app.schemas.health import HealthStatus
from backend.app.core.config import settings
from backend.app.llm.model_selector import model_selector
from backend.app.ingestion.seed_data import get_all_indexed_items

router = APIRouter()

@router.get("", response_model=HealthStatus)
async def health_check(request: Request) -> HealthStatus:
    """Returns comprehensive system health, vector database status, active model, agent tools, and provenance audit distribution."""
    vector_store = request.app.state.vector_store
    bm25_store = request.app.state.bm25_store
    agent_orchestrator = getattr(request.app.state, "agent_orchestrator", None)

    vector_count = vector_store.get_count()
    bm25_count = bm25_store.get_count()

    active_model = model_selector.active_model
    free_models = model_selector.discover_free_models()

    # Calculate live provenance distribution
    all_items = get_all_indexed_items()
    distribution = {
        "DIRECTLY_SCRAPED": 0,
        "PUBLICLY_VERIFIED_FALLBACK": 0,
        "MANUALLY_CURATED": 0,
        "UNVERIFIED": 0
    }
    for item in all_items:
        p_class = item.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
        distribution[p_class] = distribution.get(p_class, 0) + 2

    registered_tools = list(agent_orchestrator.tool_map.keys()) if agent_orchestrator else []

    return HealthStatus(
        status="HEALTHY",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        vector_db_connected=True,
        bm25_index_ready=bm25_count > 0,
        total_indexed_chunks=vector_count,
        openrouter_configured=bool(settings.OPENROUTER_API_KEY),
        active_model=active_model,
        available_free_models=free_models[:8],
        provenance_distribution=distribution,
        agentic_tools_ready=agent_orchestrator is not None,
        registered_tools=registered_tools
    )
