import pytest
import os
import shutil
from backend.app.ingestion.seed_data import SEED_PROJECTS
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.retrieval.hybrid_search import HybridRetriever
from backend.app.llm.rag_engine import RAGEngine
from backend.app.schemas.chat import ChatRequest

@pytest.fixture(scope="module")
def setup_rag():
    test_chroma = "./data/test_rag_chroma"
    test_bm25 = "./data/test_rag_bm25.pkl"

    chunker = SemanticChunker()
    v_store = VectorStore(persist_directory=test_chroma)
    b_store = BM25Store(index_path=test_bm25)

    all_chunks = []
    for item in SEED_PROJECTS:
        chunks = chunker.chunk_property(item)
        all_chunks.extend(chunks)

    v_store.add_chunks(all_chunks)
    b_store.index_chunks(all_chunks)

    retriever = HybridRetriever(vector_store=v_store, bm25_store=b_store)
    engine = RAGEngine(retriever=retriever)

    yield engine

    if os.path.exists(test_chroma):
        shutil.rmtree(test_chroma, ignore_errors=True)
    if os.path.exists(test_bm25):
        os.remove(test_bm25)

@pytest.mark.asyncio
async def test_rag_answer_grounded(setup_rag):
    engine = setup_rag
    req = ChatRequest(message="What amenities are available at DaVinci Tower by Pagani?")
    response = await engine.answer_query(req)
    assert response.answer is not None
    assert len(response.citations) > 0
    # Citations must reference DarGlobal and include canonical URL
    assert any("darglobal" in c.url.lower() for c in response.citations)
    assert response.retrieval_count > 0

@pytest.mark.asyncio
async def test_rag_comparison(setup_rag):
    engine = setup_rag
    req = ChatRequest(message="Compare Urban Oasis in Dubai vs Villa in Al Malqa Riyadh")
    response = await engine.answer_query(req)
    assert len(response.citations) >= 2
    sources = {c.source for c in response.citations}
    assert "DarGlobal" in sources or "Wasalt" in sources

@pytest.mark.asyncio
async def test_rag_unavailable_handling(setup_rag):
    engine = setup_rag
    req = ChatRequest(message="Tell me about DarGlobal's space station on Mars")
    response = await engine.answer_query(req)
    assert response.answer is not None
