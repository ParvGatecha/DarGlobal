from typing import List, Dict, Any, Optional
import re
from backend.app.core.logger import logger

class DocumentChunk:
    def __init__(self, chunk_id: str, text: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.text = text
        self.metadata = metadata

class SemanticChunker:
    """
    Transforms structured properties, sitemaps, and crawled documents into high-signal,
    searchable text chunks with preserved provenance headers and strict audit metadata.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_property(self, item: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Converts a rich property item or sitemap index into 1 or more search-optimized chunks
        with explicit provenance metadata.
        """
        chunks: List[DocumentChunk] = []

        title = item.get("title", "")
        source = item.get("source", "")
        url = item.get("url", "")
        location = item.get("location", "")
        city = item.get("city", "")
        country = item.get("country", "")
        prop_type = item.get("property_type", "")
        price = item.get("price", "Price on Application")
        brand = item.get("brand_partner") or "Independent / Signature"
        handover = item.get("handover_date") or "Ready"
        amenities = item.get("amenities", [])
        amenities_str = ", ".join(amenities) if isinstance(amenities, list) else str(amenities)
        desc = item.get("description", "")

        # Provenance attributes
        prov_class = item.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
        ext_method = item.get("extraction_method", "sitemap_discovery_and_public_dossier")
        ext_time = item.get("extraction_timestamp", "2026-11-18T17:35:40Z")
        is_direct = bool(item.get("is_directly_scraped", False))
        alt_source = item.get("alternative_source") or "None"
        origin_notes = item.get("origin_notes", "")

        # Rich context header with explicit audit provenance
        header = (
            f"PROJECT / PROPERTY: {title}\n"
            f"SOURCE: {source} ({url})\n"
            f"PROVENANCE CLASS: {prov_class} | EXTRACTION METHOD: {ext_method}\n"
            f"DIRECTLY SCRAPED: {is_direct} | TIMESTAMP: {ext_time}\n"
            f"ALTERNATIVE SOURCE: {alt_source}\n"
            f"AUDIT NOTES: {origin_notes}\n"
            f"LOCATION: {location}, {city}, {country}\n"
            f"TYPE: {prop_type} | PRICE: {price}\n"
            f"BRAND / DEVELOPER: {brand} | HANDOVER: {handover}\n"
            f"AMENITIES: {amenities_str}\n"
        )

        base_metadata = {
            "title": title,
            "source": source,
            "url": url,
            "location": location,
            "city": city,
            "country": country,
            "property_type": prop_type,
            "price": price,
            "brand_partner": brand,
            "handover_date": handover,
            "amenities": amenities_str,
            "image_url": item.get("image_url", ""),
            "provenance_class": prov_class,
            "extraction_method": ext_method,
            "extraction_timestamp": ext_time,
            "is_directly_scraped": is_direct,
            "alternative_source": alt_source,
            "origin_notes": origin_notes
        }

        # Primary Chunk 1: Full overview & specifications
        chunk_1_text = (
            f"{header}\nSUMMARY & SPECIFICATIONS:\n{desc}\n"
            f"Key Amenities Included: {amenities_str}"
        )
        chunks.append(DocumentChunk(
            chunk_id=f"{item['id']}_summary",
            text=chunk_1_text,
            metadata={**base_metadata, "section": "summary", "chunk_index": 0}
        ))

        # Secondary Chunk 2: Detailed amenities & architectural highlights
        extra_meta = item.get("metadata", {})
        meta_details = " | ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in extra_meta.items()])
        chunk_2_text = (
            f"PROJECT / PROPERTY: {title} ({source})\n"
            f"PROVENANCE: {prov_class} | AUDIT NOTE: {origin_notes}\n"
            f"LOCATION & ACCESS: Located in {location}, {city}, {country}. Handover: {handover}.\n"
            f"PRICE & UNITS: Starting at {price}. Unit Type: {prop_type}.\n"
            f"ARCHITECTURAL & INVESTMENT HIGHLIGHTS:\n{meta_details}\n"
            f"FEATURED AMENITIES:\n- " + "\n- ".join(amenities)
        )
        chunks.append(DocumentChunk(
            chunk_id=f"{item['id']}_details",
            text=chunk_2_text,
            metadata={**base_metadata, "section": "details", "chunk_index": 1}
        ))

        return chunks

    def chunk_text(
        self,
        doc_id: str,
        title: str,
        source: str,
        url: str,
        text: str,
        provenance_class: str = "DIRECTLY_SCRAPED",
        extraction_method: str = "direct_http_xml_sitemap_fetch",
        extraction_timestamp: str = "2026-11-18T17:35:40Z",
        is_directly_scraped: bool = True,
        origin_notes: str = ""
    ) -> List[DocumentChunk]:
        """
        Sliding window chunker for raw scraped text with preserved provenance metadata.
        """
        words = text.split()
        if not words:
            return []

        chunks: List[DocumentChunk] = []
        step = self.chunk_size - self.chunk_overlap
        idx = 0

        for i in range(0, len(words), step):
            segment = " ".join(words[i:i + self.chunk_size])
            chunk_text = (
                f"SOURCE: {source} ({url})\n"
                f"DOCUMENT: {title}\n"
                f"PROVENANCE: {provenance_class} | METHOD: {extraction_method}\n"
                f"AUDIT NOTE: {origin_notes}\n\n"
                f"{segment}"
            )
            chunks.append(DocumentChunk(
                chunk_id=f"{doc_id}_{idx}",
                text=chunk_text,
                metadata={
                    "title": title,
                    "source": source,
                    "url": url,
                    "chunk_index": idx,
                    "section": "web_content",
                    "provenance_class": provenance_class,
                    "extraction_method": extraction_method,
                    "extraction_timestamp": extraction_timestamp,
                    "is_directly_scraped": is_directly_scraped,
                    "origin_notes": origin_notes
                }
            ))
            idx += 1

        return chunks
