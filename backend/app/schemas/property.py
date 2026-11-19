from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

ProvenanceType = Literal[
    "DIRECTLY_SCRAPED",
    "PUBLICLY_VERIFIED_FALLBACK",
    "MANUALLY_CURATED",
    "UNVERIFIED"
]

class PropertyItem(BaseModel):
    id: str
    title: str
    source: str = Field(description="'DarGlobal' or 'Wasalt'")
    url: str
    location: str
    country: str
    city: str
    property_type: str
    result_type: Optional[str] = Field(default="PROPERTY", description="Result classification: PROPERTY, REAL_ESTATE_PROJECT, COMMERCIAL_DEVELOPMENT, XML_SITEMAP")
    price: Optional[str] = None
    currency: Optional[str] = None
    developer_or_broker: Optional[str] = None
    brand_partner: Optional[str] = None
    handover_date: Optional[str] = None
    amenities: List[str] = Field(default_factory=list)
    description: str
    image_url: Optional[str] = None
    # Strict Provenance & Authenticity Fields
    provenance_class: ProvenanceType = Field(
        default="PUBLICLY_VERIFIED_FALLBACK",
        description="Audit classification: DIRECTLY_SCRAPED, PUBLICLY_VERIFIED_FALLBACK, MANUALLY_CURATED, or UNVERIFIED"
    )
    extraction_method: str = Field(
        default="sitemap_discovery_and_public_dossier",
        description="Technical method of acquisition"
    )
    extraction_timestamp: str = Field(
        default="2026-11-18T17:35:40Z",
        description="Timestamp when data was acquired or indexed"
    )
    is_directly_scraped: bool = Field(
        default=False,
        description="True ONLY if acquired directly from target website without WAF blocks"
    )
    alternative_source: Optional[str] = Field(
        default=None,
        description="External public disclosure, press release, or market benchmark used"
    )
    origin_notes: str = Field(
        default="",
        description="Transparent audit note detailing exact provenance and security boundary context"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IngestionReport(BaseModel):
    status: str
    darglobal_sitemap_urls: int
    wasalt_sitemap_urls: int
    indexed_documents: int
    indexed_chunks: int
    vector_store_status: str
    bm25_store_status: str
    provenance_breakdown: Dict[str, int] = Field(default_factory=dict)
    waf_challenge_detected: Dict[str, bool]
    timestamp: str
