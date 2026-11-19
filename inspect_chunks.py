import json
from backend.app.retrieval.vector_store import VectorStore
from backend.app.retrieval.bm25_store import BM25Store
from backend.app.core.config import settings

vs = VectorStore(persist_directory=settings.CHROMA_PERSIST_DIRECTORY)
bm25 = BM25Store(index_path=settings.BM25_INDEX_PATH)

print(f"=== CHROMADB AUDIT ===")
print(f"Total vector chunks: {vs.get_count()}")

results = vs.collection.get(include=["metadatas", "documents"])
ids = results["ids"]
metas = results["metadatas"]
docs = results["documents"]

provenance_counts = {}
source_counts = {}
url_list = []

for i, (doc_id, meta, doc) in enumerate(zip(ids, metas, docs)):
    p_class = meta.get("provenance_class", "UNKNOWN")
    src = meta.get("source", "UNKNOWN")
    url = meta.get("url", "UNKNOWN")
    title = meta.get("title", "UNKNOWN")
    is_direct = meta.get("is_directly_scraped", False)
    
    provenance_counts[p_class] = provenance_counts.get(p_class, 0) + 1
    source_counts[src] = source_counts.get(src, 0) + 1
    url_list.append((doc_id, title, src, p_class, is_direct, url))

print("\n--- Summary Distribution ---")
print("Provenance classes:", provenance_counts)
print("Sources:", source_counts)

print("\n--- Detailed Record Inspection ---")
for doc_id, title, src, p_class, is_direct, url in url_list:
    print(f"ID: {doc_id[:35]:35} | Src: {src:10} | Class: {p_class:26} | Direct: {str(is_direct):5} | URL: {url}")

print(f"\n=== BM25 STORE AUDIT ===")
print(f"BM25 document count: {bm25.get_count()}")
print(f"BM25 and VectorStore counts match: {bm25.get_count() == vs.get_count()}")
