import pytest
from backend.app.ingestion.seed_data import get_all_indexed_items, SEED_PROJECTS, DIRECT_SCRAPED_SITEMAP_RECORDS
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.schemas.property import PropertyItem
from backend.app.schemas.chat import Citation

def test_provenance_valid_classifications():
    valid_classes = {"DIRECTLY_SCRAPED", "PUBLICLY_VERIFIED_FALLBACK", "MANUALLY_CURATED", "UNVERIFIED"}
    items = get_all_indexed_items()
    assert len(items) >= 16

    for item in items:
        p_class = item.get("provenance_class")
        assert p_class in valid_classes
        assert p_class != "UNVERIFIED", f"Item {item.get('id')} must not be unverified!"
        assert "extraction_method" in item
        assert "extraction_timestamp" in item
        assert "origin_notes" in item

        # Strict rule: is_directly_scraped can only be True if provenance_class is DIRECTLY_SCRAPED
        if item.get("is_directly_scraped"):
            assert p_class == "DIRECTLY_SCRAPED"

def test_chunker_propagates_provenance():
    chunker = SemanticChunker()
    items = get_all_indexed_items()

    for item in items:
        chunks = chunker.chunk_property(item)
        assert len(chunks) >= 2
        for c in chunks:
            meta = c.metadata
            assert "provenance_class" in meta
            assert meta["provenance_class"] == item["provenance_class"]
            assert meta["extraction_method"] == item["extraction_method"]
            assert meta["is_directly_scraped"] == item["is_directly_scraped"]
            assert "PROVENANCE" in c.text

def test_sitemap_records_are_directly_scraped():
    for rec in DIRECT_SCRAPED_SITEMAP_RECORDS:
        assert rec["provenance_class"] == "DIRECTLY_SCRAPED"
        assert rec["is_directly_scraped"] is True
        assert "sitemap" in rec["url"]

def test_property_dossiers_are_verified_fallbacks():
    for p in SEED_PROJECTS:
        assert p["provenance_class"] == "PUBLICLY_VERIFIED_FALLBACK"
        assert p["is_directly_scraped"] is False
        assert p["alternative_source"] is not None
        assert len(p["origin_notes"]) > 20
