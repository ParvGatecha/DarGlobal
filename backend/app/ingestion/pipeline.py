import datetime
from typing import Dict, Any
from backend.app.ingestion.crawler import EthicalCrawler
from backend.app.ingestion.seed_data import SEED_PROJECTS, DIRECT_SCRAPED_SITEMAP_RECORDS, get_all_indexed_items
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.schemas.property import IngestionReport
from backend.app.core.logger import logger

class IngestionPipeline:
    """
    End-to-end ingestion orchestrator for DarGlobal and Wasalt real estate data,
    incorporating strict data provenance auditing and classification.
    """

    def __init__(self, vector_store: VectorStore, bm25_store: BM25Store):
        self.crawler = EthicalCrawler()
        self.chunker = SemanticChunker()
        self.vector_store = vector_store
        self.bm25_store = bm25_store

    def run(self, probe_live: bool = True) -> IngestionReport:
        logger.info("Starting DarGlobal Intelligence Ingestion Pipeline with Provenance Audit...")
        start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Step 1: Discover sitemaps
        if probe_live:
            dg_urls = self.crawler.fetch_darglobal_sitemap()
            ws_urls = self.crawler.fetch_wasalt_sitemap()
            waf_detected = {"darglobal_hcaptcha": True, "wasalt_turnstile": True}
            if dg_urls:
                sample_dg = self.crawler.inspect_url_security(dg_urls[0])
                waf_detected["darglobal_hcaptcha"] = sample_dg["waf_detected"]
            if ws_urls:
                sample_ws = self.crawler.inspect_url_security(ws_urls[0])
                waf_detected["wasalt_turnstile"] = sample_ws["waf_detected"]
        else:
            # Deterministic, zero-network instant boot from canonical sitemap records
            dg_urls = [r["url"] for r in DIRECT_SCRAPED_SITEMAP_RECORDS if "darglobal" in r.get("url", "")]
            ws_urls = [r["url"] for r in DIRECT_SCRAPED_SITEMAP_RECORDS if "wasalt" in r.get("url", "")]
            waf_detected = {"darglobal_hcaptcha": True, "wasalt_turnstile": True}

        # Step 3: Chunk authoritative verified real estate datasets & directly scraped sitemaps
        all_items = get_all_indexed_items()
        all_chunks = []
        provenance_breakdown: Dict[str, int] = {
            "DIRECTLY_SCRAPED": 0,
            "PUBLICLY_VERIFIED_FALLBACK": 0,
            "MANUALLY_CURATED": 0,
            "UNVERIFIED": 0
        }

        import os
        from backend.app.core.config import settings
        canonical_path = getattr(settings, "CANONICAL_DATASET_PATH", "./backend/data/canonical_dataset.json")
        if not probe_live and os.path.exists(canonical_path):
            try:
                import json
                with open(canonical_path, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                from backend.app.ingestion.chunker import DocumentChunk
                all_chunks = [
                    DocumentChunk(c["chunk_id"], c["text"], c["metadata"])
                    for c in cdata.get("chunks", [])
                ]
                for c in all_chunks:
                    p_class = c.metadata.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                    provenance_breakdown[p_class] = provenance_breakdown.get(p_class, 0) + 1
                logger.info(f"Loaded {len(all_chunks)} canonical chunks directly from {canonical_path}")
            except Exception as e:
                logger.warning(f"Could not load canonical JSON ({e}), falling back to dynamic chunker.")
                all_chunks = []

        if not all_chunks:
            for item in all_items:
                chunks = self.chunker.chunk_property(item)
                p_class = item.get("provenance_class", "PUBLICLY_VERIFIED_FALLBACK")
                provenance_breakdown[p_class] = provenance_breakdown.get(p_class, 0) + len(chunks)
                all_chunks.extend(chunks)

        logger.info(
            f"Generated {len(all_chunks)} semantic chunks from {len(all_items)} records. "
            f"Provenance breakdown: {provenance_breakdown}"
        )

        # Step 4: Index into ChromaDB Vector Store
        self.vector_store.add_chunks(all_chunks)

        # Step 5: Index into BM25 Lexical Store
        self.bm25_store.index_chunks(all_chunks)

        report = IngestionReport(
            status="SUCCESS",
            darglobal_sitemap_urls=len(dg_urls),
            wasalt_sitemap_urls=len(ws_urls),
            indexed_documents=len(all_items),
            indexed_chunks=len(all_chunks),
            vector_store_status=f"Active ({self.vector_store.get_count()} chunks)",
            bm25_store_status=f"Active ({self.bm25_store.get_count()} chunks)",
            provenance_breakdown=provenance_breakdown,
            waf_challenge_detected=waf_detected,
            timestamp=start_time
        )
        logger.info(f"Ingestion pipeline completed successfully: {report.model_dump()}")
        return report
