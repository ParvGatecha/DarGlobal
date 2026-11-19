from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from backend.app.schemas.property import PropertyItem
from backend.app.ingestion.seed_data import get_all_indexed_items, is_allowed_property_result

router = APIRouter()

@router.get("", response_model=List[PropertyItem])
async def list_properties(
    source: Optional[str] = Query(None, description="Filter by 'DarGlobal' or 'Wasalt'"),
    city: Optional[str] = Query(None, description="Filter by city name (e.g. Dubai, Riyadh, Muscat)"),
    search: Optional[str] = Query(None, description="Search keyword in title, developer, or amenities"),
    provenance: Optional[str] = Query(None, description="Filter by provenance class (DIRECTLY_SCRAPED, PUBLICLY_VERIFIED_FALLBACK)"),
    include_sitemaps: bool = Query(False, description="Whether to include raw sitemap index documents")
) -> List[PropertyItem]:
    """Lists indexed properties with optional filtering. Sitemaps are excluded by default."""
    results = []
    search_lower = search.lower() if search else ""
    all_items = get_all_indexed_items()

    for raw in all_items:
        if not include_sitemaps and not is_allowed_property_result(raw):
            continue
        item = PropertyItem(**raw)
        if source and source.lower() not in item.source.lower():
            continue
        if city and city.lower() not in item.city.lower():
            continue
        if provenance and provenance.upper() != item.provenance_class:
            continue
        if search_lower:
            text_haystack = f"{item.title} {item.description} {item.location} {item.developer_or_broker or ''} {' '.join(item.amenities)} {item.origin_notes}".lower()
            if search_lower not in text_haystack:
                continue
        results.append(item)

    return results

@router.get("/{property_id}", response_model=PropertyItem)
async def get_property(property_id: str) -> PropertyItem:
    """Retrieve detailed specs and provenance for a single property item."""
    all_items = get_all_indexed_items()
    for raw in all_items:
        if raw["id"] == property_id:
            return PropertyItem(**raw)
    raise HTTPException(status_code=404, detail="Property record not found")
