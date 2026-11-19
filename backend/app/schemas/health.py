from typing import List, Dict
from pydantic import BaseModel, Field

class HealthStatus(BaseModel):
    status: str
    project: str
    version: str
    vector_db_connected: bool
    bm25_index_ready: bool
    total_indexed_chunks: int
    openrouter_configured: bool
    active_model: str
    available_free_models: List[str]
    provenance_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of indexed chunks by provenance class"
    )
    agentic_tools_ready: bool = Field(
        default=True,
        description="Indicates whether the Agent Orchestration Layer and its 6 tools are loaded"
    )
    registered_tools: List[str] = Field(
        default_factory=list,
        description="List of genuine tools available to the agent"
    )
