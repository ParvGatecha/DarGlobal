import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.ingestion.chunker import DocumentChunk

class VectorStore:
    """
    Persistent ChromaDB vector store for dense semantic retrieval.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection_name = "darglobal_intelligence"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"VectorStore initialized at {self.persist_directory} with {self.collection.count()} chunks.")

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Adds a list of document chunks into ChromaDB."""
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [c.metadata for c in chunks]

        # ChromaDB requires primitive metadata values
        cleaned_metadatas = []
        for m in metadatas:
            cleaned = {}
            for k, v in m.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                elif v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
            cleaned_metadatas.append(cleaned)

        # Batch upsert
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=cleaned_metadatas[i:i + batch_size]
            )
        logger.info(f"Successfully upserted {len(chunks)} chunks into ChromaDB. Total count: {self.collection.count()}")

    def search(self, query: str, top_k: int = 10, source_filter: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB collection using dense cosine distance.
        Returns ordered list of hit dictionaries.
        """
        if "n_results" in kwargs:
            top_k = kwargs["n_results"]
        where_filter = None
        if source_filter and source_filter.lower() in ["darglobal", "wasalt"]:
            filter_val = "DarGlobal" if source_filter.lower() == "darglobal" else "Wasalt"
            where_filter = {"source": filter_val}

        total_docs = self.collection.count()
        if total_docs == 0:
            return []

        actual_k = min(top_k, total_docs)
        kwargs = {
            "query_texts": [query],
            "n_results": actual_k,
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = self.collection.query(**kwargs)

        hits: List[Dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return hits

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(ids)

        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, distances)):
            # Cosine distance to similarity: 1.0 - distance
            similarity = max(0.0, 1.0 - dist)
            hits.append({
                "chunk_id": cid,
                "text": doc,
                "metadata": meta,
                "score": similarity,
                "dense_rank": rank + 1
            })

        return hits

    def get_count(self) -> int:
        return self.collection.count()

    def reset(self):
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("ChromaDB collection reset.")
