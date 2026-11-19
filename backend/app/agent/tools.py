import re
import time
from typing import List, Dict, Any, Optional
from backend.app.core.logger import logger
from backend.app.retrieval.hybrid_search import HybridSearchEngine
from backend.app.ingestion.seed_data import get_all_indexed_items, SEED_PROJECTS, DIRECT_SCRAPED_SITEMAP_RECORDS
from backend.app.schemas.agent import (
    SearchDarGlobalInput,
    SearchWasaltInput,
    SearchByLocationInput,
    GetProjectDetailsInput,
    ComparePropertiesInput,
    GetSourceInformationInput,
)

def _parse_numeric_price(price_str: Optional[str]) -> Optional[float]:
    """Extracts numeric price value from formatted currency string."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None

class AgentToolRegistry:
    """
    Registry of validated tools for DarGlobal Intelligence Agent.
    Executes real queries against ChromaDB, BM25, and verified property dossiers.
    Never fabricates data; returns authentic records with citations and provenance.
    """

    def __init__(self, retriever: HybridSearchEngine):
        self.retriever = retriever
        self.all_items = get_all_indexed_items()

    def search_darglobal_projects(self, params: SearchDarGlobalInput) -> Dict[str, Any]:
        """Search indexed DarGlobal project information."""
        query = params.query
        city_filter = params.city.lower() if params.city else None
        country_filter = params.country.lower() if params.country else None

        # Query hybrid retrieval for DarGlobal chunks
        hybrid_hits = self.retriever.search(
            query=query,
            k_results=params.max_results * 2,
            source_filter="darglobal"
        )

        # Cross-reference with structured seed projects for complete attributes
        results = []
        seen_ids = set()

        for item in SEED_PROJECTS:
            if item.get("source", "").lower() != "darglobal":
                continue

            # Apply city filter
            if city_filter and city_filter not in item.get("city", "").lower() and city_filter not in item.get("location", "").lower():
                continue

            # Apply country filter
            if country_filter and country_filter not in item.get("country", "").lower():
                continue

            # Check query relevance
            haystack = f"{item['title']} {item['location']} {item['description']} {item.get('brand_partner', '')} {' '.join(item['amenities'])}".lower()
            if any(term in haystack for term in query.lower().split() if len(term) > 2) or not query.strip():
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    results.append({
                        "id": item["id"],
                        "title": item["title"],
                        "source": item["source"],
                        "url": item["url"],
                        "location": f"{item['location']}, {item['city']}, {item['country']}",
                        "property_type": item["property_type"],
                        "price": item.get("price"),
                        "currency": item.get("currency"),
                        "brand_partner": item.get("brand_partner"),
                        "handover_date": item.get("handover_date"),
                        "key_amenities": item["amenities"][:4],
                        "description": item["description"],
                        "provenance_class": item.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                    })

        # If strict filter didn't match all, supplement from hybrid hits
        if len(results) < params.max_results:
            for hit in hybrid_hits:
                meta = hit.get("metadata", {})
                item_id = meta.get("id") or hit.get("chunk_id", "").split("_")[0]
                if item_id and item_id not in seen_ids and meta.get("source", "").lower() == "darglobal":
                    seen_ids.add(item_id)
                    results.append({
                        "id": item_id,
                        "title": meta.get("title"),
                        "source": meta.get("source"),
                        "url": meta.get("url"),
                        "location": f"{meta.get('location', '')}, {meta.get('city', '')}, {meta.get('country', '')}",
                        "property_type": meta.get("property_type"),
                        "price": meta.get("price"),
                        "brand_partner": meta.get("brand_partner"),
                        "handover_date": meta.get("handover_date"),
                        "provenance_class": meta.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                    })

        trimmed = results[:params.max_results]
        return {
            "query": query,
            "count": len(trimmed),
            "source_filter": "DarGlobal",
            "projects": trimmed
        }

    def search_wasalt_properties(self, params: SearchWasaltInput) -> Dict[str, Any]:
        """Search indexed Wasalt property information."""
        query = params.query
        city_filter = params.city.lower() if params.city else None
        prop_type_filter = params.property_type.lower() if params.property_type else None
        max_budget = params.max_budget_sar
        min_budget = params.min_budget_sar

        results = []
        seen_ids = set()

        for item in SEED_PROJECTS:
            if item.get("source", "").lower() != "wasalt":
                continue

            # City filter
            if city_filter and city_filter not in item.get("city", "").lower() and city_filter not in item.get("location", "").lower():
                continue

            # Property type filter
            if prop_type_filter and prop_type_filter not in item.get("property_type", "").lower():
                continue

            # Budget filtering in SAR
            num_price = _parse_numeric_price(item.get("price"))
            if max_budget is not None and num_price is not None:
                if num_price > max_budget:
                    continue
            if min_budget is not None and num_price is not None:
                if num_price < min_budget:
                    continue

            # Textual relevance
            haystack = f"{item['title']} {item['location']} {item['description']} {item['property_type']} {' '.join(item['amenities'])}".lower()
            query_terms = [t for t in query.lower().split() if len(t) > 2]
            if not query_terms or any(term in haystack for term in query_terms):
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    results.append({
                        "id": item["id"],
                        "title": item["title"],
                        "source": item["source"],
                        "url": item["url"],
                        "location": f"{item['location']}, {item['city']}, {item['country']}",
                        "property_type": item["property_type"],
                        "price": item.get("price"),
                        "numeric_price_sar": num_price,
                        "developer_or_broker": item.get("developer_or_broker"),
                        "handover_date": item.get("handover_date"),
                        "key_amenities": item["amenities"][:4],
                        "description": item["description"],
                        "provenance_class": item.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                    })

        trimmed = results[:params.max_results]
        return {
            "query": query,
            "count": len(trimmed),
            "source_filter": "Wasalt",
            "budget_applied": {
                "max_budget_sar": max_budget,
                "min_budget_sar": min_budget
            },
            "properties": trimmed
        }

    def search_by_location(self, params: SearchByLocationInput) -> Dict[str, Any]:
        """Retrieve properties and projects matching a location."""
        loc = params.location.lower().strip()
        source_filter = params.source_filter.lower() if params.source_filter else None

        results = []
        seen_ids = set()

        for item in self.all_items:
            # Check source filter
            if source_filter:
                if source_filter not in item.get("source", "").lower():
                    continue

            loc_haystack = f"{item.get('location', '')} {item.get('city', '')} {item.get('country', '')} {item.get('title', '')}".lower()
            if loc in loc_haystack or any(term in loc_haystack for term in loc.split() if len(term) > 2):
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    results.append({
                        "id": item["id"],
                        "title": item["title"],
                        "source": item["source"],
                        "url": item["url"],
                        "location": item.get("location"),
                        "city": item.get("city"),
                        "country": item.get("country"),
                        "property_type": item.get("property_type"),
                        "price": item.get("price"),
                        "provenance_class": item.get("provenance_class")
                    })

        trimmed = results[:params.max_results]
        return {
            "location_queried": params.location,
            "source_filter": params.source_filter or "all",
            "count": len(trimmed),
            "matches": trimmed
        }

    def get_project_details(self, params: GetProjectDetailsInput) -> Dict[str, Any]:
        """Retrieve detailed information about a specific project."""
        p_id = params.project_id.lower().strip() if params.project_id else None
        p_name = params.project_name.lower().strip() if params.project_name else None

        if not p_id and not p_name:
            return {"error": "Either project_id or project_name must be supplied."}

        matched = None
        for item in self.all_items:
            if p_id and p_id in item.get("id", "").lower():
                matched = item
                break
            if p_name and (p_name in item.get("title", "").lower() or p_name in item.get("id", "").lower()):
                matched = item
                break

        if not matched:
            available_titles = [i["title"] for i in self.all_items if "title" in i]
            return {
                "error": f"Project not found for query (id={p_id}, name={p_name})",
                "available_projects_suggestion": available_titles[:6]
            }

        return {
            "found": True,
            "id": matched["id"],
            "title": matched["title"],
            "source": matched["source"],
            "url": matched["url"],
            "location": matched.get("location"),
            "city": matched.get("city"),
            "country": matched.get("country"),
            "property_type": matched.get("property_type"),
            "price": matched.get("price"),
            "currency": matched.get("currency"),
            "developer_or_broker": matched.get("developer_or_broker"),
            "brand_partner": matched.get("brand_partner"),
            "handover_date": matched.get("handover_date"),
            "amenities": matched.get("amenities", []),
            "description": matched.get("description", ""),
            "metadata": matched.get("metadata", {}),
            "provenance_class": matched.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK"),
            "extraction_method": matched.get("extraction_method"),
            "extraction_timestamp": matched.get("extraction_timestamp"),
            "alternative_source": matched.get("alternative_source"),
            "origin_notes": matched.get("origin_notes")
        }

    def compare_properties(self, params: ComparePropertiesInput) -> Dict[str, Any]:
        """Compare two or more properties using verified attributes."""
        targets = params.property_names_or_ids
        focus_attrs = params.focus_attributes or [
            "price",
            "location",
            "property_type",
            "handover_date",
            "brand_partner",
            "amenities",
            "provenance_class"
        ]

        found_properties = []
        for target in targets:
            target_clean = target.lower().strip()
            item_match = None
            for item in self.all_items:
                if target_clean in item.get("id", "").lower() or target_clean in item.get("title", "").lower():
                    item_match = item
                    break
            if item_match:
                extracted = {
                    "id": item_match["id"],
                    "title": item_match["title"],
                    "source": item_match["source"],
                    "url": item_match["url"],
                }
                for attr in focus_attrs:
                    if attr == "amenities":
                        extracted[attr] = item_match.get("amenities", [])[:5]
                    else:
                        extracted[attr] = item_match.get(attr)
                found_properties.append(extracted)

        if len(found_properties) < 2:
            return {
                "error": f"Could not find at least two properties from input list: {targets}",
                "resolved_count": len(found_properties),
                "resolved": found_properties
            }

        return {
            "comparison_count": len(found_properties),
            "focus_attributes": focus_attrs,
            "compared_properties": found_properties,
            "verification_note": "Comparison constructed exclusively from verified, indexed attributes without fabrication."
        }

    def get_source_information(self, params: GetSourceInformationInput) -> Dict[str, Any]:
        """Retrieve provenance and original URLs."""
        query = params.query_or_url.lower().strip()

        matched = None
        for item in self.all_items:
            if (
                query in item.get("url", "").lower()
                or query in item.get("id", "").lower()
                or query in item.get("title", "").lower()
            ):
                matched = item
                break

        if not matched:
            return {
                "found": False,
                "query": params.query_or_url,
                "message": "No matching record or URL found in indexed provenance registry."
            }

        return {
            "found": True,
            "id": matched["id"],
            "title": matched["title"],
            "source_platform": matched["source"],
            "canonical_url": matched["url"],
            "provenance_class": matched.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK"),
            "is_directly_scraped": matched.get("is_directly_scraped", False),
            "extraction_method": matched.get("extraction_method"),
            "extraction_timestamp": matched.get("extraction_timestamp"),
            "alternative_source": matched.get("alternative_source"),
            "origin_notes": matched.get("origin_notes")
        }

# Tool Definitions formatted for OpenRouter / OpenAI Function Calling API
AGENT_OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_darglobal_projects",
            "description": "Search indexed DarGlobal luxury real estate project information across Dubai, Marbella, Muscat, Qatar, and London.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms or keywords (e.g. 'Pagani', 'Lamborghini', 'beachfront', 'villas', 'penthouses')"
                    },
                    "city": {
                        "type": "string",
                        "description": "City filter e.g. 'Dubai', 'Marbella', 'Muscat', 'Doha', 'Riyadh'"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country filter e.g. 'UAE', 'Spain', 'Oman', 'Qatar', 'Saudi Arabia'"
                    },
                    "max_budget_usd": {
                        "type": "number",
                        "description": "Optional upper budget limit in USD"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of projects to return"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_wasalt_properties",
            "description": "Search indexed Wasalt Saudi real estate marketplace properties across Riyadh, Jeddah, and Al Khobar with budget filtering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms (e.g. 'smart villa', 'sea view apartment', 'duplex', 'commercial office')"
                    },
                    "city": {
                        "type": "string",
                        "description": "Saudi city filter e.g. 'Riyadh', 'Jeddah', 'Al Khobar'"
                    },
                    "property_type": {
                        "type": "string",
                        "description": "Property category: 'Villa', 'Duplex', 'Apartment', 'Commercial Floor'"
                    },
                    "max_budget_sar": {
                        "type": "number",
                        "description": "Upper budget limit in Saudi Riyals (SAR), e.g. 2000000 for SAR 2 million"
                    },
                    "min_budget_sar": {
                        "type": "number",
                        "description": "Lower budget limit in Saudi Riyals (SAR)"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of properties to return"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_location",
            "description": "Retrieve properties and projects matching a specific location, city, district, or country across both DarGlobal and Wasalt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name e.g. 'Riyadh', 'Al Malqa', 'Dubai', 'Business Bay', 'Jeddah', 'Marbella', 'Muscat'"
                    },
                    "source_filter": {
                        "type": "string",
                        "enum": ["DarGlobal", "Wasalt"],
                        "description": "Optional platform filter"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 6,
                        "description": "Maximum results to retrieve"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_details",
            "description": "Retrieve comprehensive verified specs, amenities, pricing, handover dates, and partner brands for a specific project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Unique identifier e.g. 'dg-pagani-geometria', 'ws-villa-malqa-riyadh', 'dg-tierra-viva-marbella'"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name or title e.g. 'DaVinci Tower', 'Pagani', 'Tierra Viva', 'Urban Oasis', 'Malqa Villa'"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_properties",
            "description": "Compare two or more real estate properties using verified factual attributes without hallucination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_names_or_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 2 to 5 property titles or IDs to compare"
                    },
                    "focus_attributes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional attributes to focus on e.g. ['price', 'location', 'amenities', 'handover_date']"
                    }
                },
                "required": ["property_names_or_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_source_information",
            "description": "Retrieve verifiable data provenance, original URLs, extraction methodology, and security boundary notes for any record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_url": {
                        "type": "string",
                        "description": "Property title, document ID, or URL to inspect"
                    }
                },
                "required": ["query_or_url"]
            }
        }
    }
]
