import os
import shutil
import tempfile
import pytest
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.retrieval.hybrid_search import HybridRetriever


def test_ephemeral_chromadb_recovery_after_restart():
    """
    Simulates Render Free ephemeral disk environment:
    1. Disk starts empty with no existing database.
    2. Backend starts up and triggers deterministic bootstrap.
    3. Reconstructs all 32 chunks with 100% provenance fidelity.
    4. Second run verifies idempotency (no duplicates).
    5. Verifies hybrid search operations on recovered stores.
    """
    temp_dir = tempfile.mkdtemp(prefix="test_render_ephemeral_")
    chroma_dir = os.path.join(temp_dir, "chroma_db")
    bm25_path = os.path.join(temp_dir, "bm25_index.pkl")

    try:
        # Phase 1: Clean startup on empty disk
        vs = VectorStore(persist_directory=chroma_dir)
        bm = BM25Store(index_path=bm25_path)

        assert vs.get_count() == 0, "ChromaDB should initially be empty"
        assert bm.get_count() == 0, "BM25 should initially be empty"

        pipeline = IngestionPipeline(vector_store=vs, bm25_store=bm)
        report = pipeline.run(probe_live=False)

        # Phase 2: Verify all 32 chunks recovered
        assert report.status == "SUCCESS"
        assert vs.get_count() == 32, f"Expected 32 chunks, got {vs.get_count()}"
        assert bm.get_count() == 32, f"Expected 32 BM25 docs, got {bm.get_count()}"

        # Phase 3: Verify provenance distribution preservation
        breakdown = report.provenance_breakdown
        assert breakdown["DIRECTLY_SCRAPED"] == 4, "Directly scraped sitemaps must equal 4 chunks"
        assert breakdown["PUBLICLY_VERIFIED_FALLBACK"] == 28, "Publicly verified fallbacks must equal 28 chunks"
        assert breakdown["MANUALLY_CURATED"] == 0
        assert breakdown["UNVERIFIED"] == 0

        # Phase 4: Idempotency check (running again must NOT duplicate documents)
        report_second = pipeline.run(probe_live=False)
        assert vs.get_count() == 32, "ChromaDB count must remain 32 after second run (idempotent upsert)"
        assert bm.get_count() == 32, "BM25 count must remain 32 after second run"

        # Phase 5: Query accuracy on recovered stores
        retriever = HybridRetriever(vector_store=vs, bm25_store=bm)

        # Check DarGlobal Dubai project retrieval
        hits_dg = retriever.retrieve("DaVinci Pagani Tower Dubai", k_results=3)
        assert len(hits_dg) >= 1
        pagani_hits = [h for h in hits_dg if "pagani" in h["metadata"].get("title", "").lower()]
        assert len(pagani_hits) >= 1, f"Expected Pagani in hits, got: {[h['metadata'].get('title') for h in hits_dg]}"
        meta_dg = pagani_hits[0]["metadata"]
        assert "pagani" in meta_dg.get("title", "").lower()
        assert "darglobal.co.uk" in meta_dg.get("url", "")
        assert meta_dg.get("provenance_class") == "PUBLICLY_VERIFIED_FALLBACK"

        # Check Wasalt Riyadh property retrieval
        hits_ws = retriever.retrieve("Al Malqa smart villa Riyadh", k_results=3)
        assert len(hits_ws) >= 1
        malqa_hits = [h for h in hits_ws if "malqa" in h["metadata"].get("title", "").lower() or "malqa" in h["metadata"].get("location", "").lower()]
        assert len(malqa_hits) >= 1, f"Expected Malqa in hits, got: {[h['metadata'].get('title') for h in hits_ws]}"
        meta_ws = malqa_hits[0]["metadata"]
        assert "wasalt.sa" in meta_ws.get("url", "")
        assert meta_ws.get("provenance_class") == "PUBLICLY_VERIFIED_FALLBACK"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
