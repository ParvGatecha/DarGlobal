from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from backend.app.schemas.agent import ToolExecutionTrace

ProvenanceType = Literal[
    "DIRECTLY_SCRAPED",
    "PUBLICLY_VERIFIED_FALLBACK",
    "MANUALLY_CURATED",
    "UNVERIFIED"
]

class Citation(BaseModel):
    citation_id: int
    title: str
    url: str
    source: str = Field(description="'DarGlobal' or 'Wasalt'")
    snippet: str
    provenance_class: ProvenanceType = Field(
        default="PUBLICLY_VERIFIED_FALLBACK",
        description="Audit classification: DIRECTLY_SCRAPED, PUBLICLY_VERIFIED_FALLBACK, MANUALLY_CURATED, or UNVERIFIED"
    )
    extraction_method: str = Field(
        default="sitemap_discovery_and_public_dossier",
        description="Method used to obtain or verify document"
    )
    extraction_timestamp: str = Field(
        default="2026-11-18T17:35:40Z",
        description="Timestamp of acquisition or indexing"
    )
    is_directly_scraped: bool = Field(
        default=False,
        description="True ONLY if acquired directly from target website without WAF blocks"
    )
    alternative_source: Optional[str] = Field(
        default=None,
        description="Alternative source or disclosure"
    )
    origin_notes: str = Field(
        default="",
        description="Audit trail and security boundary notes"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatMessage(BaseModel):
    role: str = Field(description="'user' or 'assistant' or 'system'")
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    source_filter: Optional[str] = Field(default=None, description="'all', 'darglobal', or 'wasalt'")
    top_k: Optional[int] = Field(default=5, description="Number of hybrid documents to retrieve")

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    model_used: str
    retrieval_count: int
    provenance_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of retrieved citations by provenance classification"
    )
    execution_trace: List[ToolExecutionTrace] = Field(
        default_factory=list,
        description="Audit trace of tools actually executed by the agent"
    )
    execution_time_ms: float
