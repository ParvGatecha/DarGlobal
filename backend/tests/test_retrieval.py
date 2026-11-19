import pytest
import os
import shutil
from backend.app.ingestion.seed_data import SEED_PROJECTS
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.retrieval.hybrid_search import HybridRetriever

@pytest.fixture(scope="module")
def setup_stores():
    test_chroma = "./data/test_chroma_db"
    test_bm25 = "./data/test_bm25_index.pkl"

    chunker = SemanticChunker()
    v_store = VectorStore(persist_directory=test_chroma)
    b_store = BM25Store(index_path=test_bm25)

    all_chunks = []
    for item in SEED_PROJECTS:
        chunks = chunker.chunk_property(item)
        all_chunks.extend(chunks)

    v_store.add_chunks(all_chunks)
    b_store.index_chunks(all_chunks)

    yield v_store, b_store, all_chunks

    # Cleanup
    if os.path.exists(test_chroma):
        shutil.rmtree(test_chroma, ignore_errors=True)
    if os.path.exists(test_bm25):
        os.remove(test_bm25)

def test_chunking_and_indexing(setup_stores):
    v_store, b_store, chunks = setup_stores
    assert len(chunks) >= len(SEED_PROJECTS) * 2
    assert v_store.get_count() == len(chunks)
    assert b_store.get_count() == len(chunks)

def test_hybrid_search_pagani(setup_stores):
    v_store, b_store, _ = setup_stores
    retriever = HybridRetriever(vector_store=v_store, bm25_store=b_store)
    hits = retriever.retrieve("What is the price and location of Pagani DaVinci tower in Dubai?")
    assert len(hits) > 0
    top_hit = hits[0]
    assert "Pagani" in top_hit["text"] or "DaVinci" in top_hit["text"]
    assert top_hit["metadata"]["source"] == "DarGlobal"

def test_hybrid_search_wasalt(setup_stores):
    v_store, b_store, _ = setup_stores
    retriever = HybridRetriever(vector_store=v_store, bm25_store=b_store)
    hits = retriever.retrieve("Find a luxury smart villa in Al Malqa Riyadh", source_filter="wasalt")
    assert len(hits) > 0
    assert any("Malqa" in h["text"] for h in hits)
    assert hits[0]["metadata"]["source"] == "Wasalt"

def test_citations_formatting(setup_stores):
    v_store, b_store, _ = setup_stores
    retriever = HybridRetriever(vector_store=v_store, bm25_store=b_store)
    hits = retriever.retrieve("Tierra Viva Lamborghini Marbella")
    citations = retriever.format_citations(hits)
    assert len(citations) > 0
    assert citations[0].citation_id == 1
    assert "https://" in citations[0].url
    assert citations[0].source in ["DarGlobal", "Wasalt"]
