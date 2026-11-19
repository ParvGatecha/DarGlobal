from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

ToolStatus = Literal["SUCCESS", "ERROR", "TIMEOUT", "SKIPPED"]

class ToolExecutionTrace(BaseModel):
    """
    Audit log of an individual tool execution performed by the agent.
    Never fabricated: records actual code execution and metrics.
    """
    step: int = Field(description="Execution step number (1-based)")
    tool_name: str = Field(description="Name of the executed tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Validated arguments passed to tool")
    execution_time_ms: float = Field(description="Time taken to execute tool in milliseconds")
    status: ToolStatus = Field(default="SUCCESS", description="Execution outcome")
    result_summary: str = Field(description="Concise factual summary of output")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Raw structured tool output")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")

# Tool Input Schemas with Pydantic Validation

class SearchDarGlobalInput(BaseModel):
    query: str = Field(description="Search keywords for DarGlobal luxury branded projects")
    city: Optional[str] = Field(default=None, description="City filter: Dubai, Muscat, Doha, Marbella, Riyadh")
    country: Optional[str] = Field(default=None, description="Country filter: UAE, Oman, Qatar, Spain, Saudi Arabia")
    max_budget_usd: Optional[float] = Field(default=None, description="Maximum budget constraint in USD")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum results to return")

class SearchWasaltInput(BaseModel):
    query: str = Field(description="Search keywords for Wasalt Saudi marketplace properties")
    city: Optional[str] = Field(default=None, description="Saudi city filter: Riyadh, Jeddah, Al Khobar")
    property_type: Optional[str] = Field(default=None, description="Property category: Villa, Duplex, Apartment, Commercial Floor")
    max_budget_sar: Optional[float] = Field(default=None, description="Maximum price in Saudi Riyals (SAR)")
    min_budget_sar: Optional[float] = Field(default=None, description="Minimum price in Saudi Riyals (SAR)")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum results to return")

class SearchByLocationInput(BaseModel):
    location: str = Field(description="Target location, city, district, or geographic region (e.g. Riyadh, Al Malqa, Downtown Dubai, Jeddah, Marbella)")
    source_filter: Optional[str] = Field(default=None, description="Filter by source platform: 'DarGlobal', 'Wasalt', or None for both")
    max_results: int = Field(default=6, ge=1, le=12, description="Maximum results to return")

class GetProjectDetailsInput(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Exact ID of the property e.g. 'dg-pagani-geometria', 'ws-villa-malqa-riyadh'")
    project_name: Optional[str] = Field(default=None, description="Property title or name e.g. 'DaVinci Tower', 'Tierra Viva', 'Al Malqa Villa'")

class ComparePropertiesInput(BaseModel):
    property_names_or_ids: List[str] = Field(
        min_length=2,
        max_length=5,
        description="List of at least two property names or IDs to compare"
    )
    focus_attributes: Optional[List[str]] = Field(
        default=None,
        description="Attributes to compare: price, location, property_type, handover_date, amenities, brand_partner, developer"
    )

class GetSourceInformationInput(BaseModel):
    query_or_url: str = Field(description="Property title, document ID, or URL to retrieve verified provenance and extraction audit trail")
