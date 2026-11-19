import os
import pickle
import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.ingestion.chunker import DocumentChunk

class BM25Store:
    """
    High-speed lexical search engine using Rank-BM25.
    Specialized for exact brand, location, price, and spec matches.
    """

    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path or settings.BM25_INDEX_PATH
        self.bm25: Optional[BM25Okapi] = None
        self.chunk_ids: List[str] = []
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.load_index()

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric words."""
        return re.findall(r"\w+", text.lower())

    def index_chunks(self, chunks: List[DocumentChunk]):
        """Build and persist BM25 index from document chunks."""
        if not chunks:
            return

        self.chunk_ids = [c.chunk_id for c in chunks]
        self.documents = [c.text for c in chunks]
        self.metadatas = [c.metadata for c in chunks]

        tokenized_corpus = [self.tokenize(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Save to disk
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        with open(self.index_path, "wb") as f:
            pickle.dump({
                "chunk_ids": self.chunk_ids,
                "documents": self.documents,
                "metadatas": self.metadatas
            }, f)
        logger.info(f"Persisted BM25 index with {len(self.documents)} documents to {self.index_path}")

    def load_index(self):
        """Loads index from disk if it exists."""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "rb") as f:
                    data = pickle.load(f)
                    self.chunk_ids = data["chunk_ids"]
                    self.documents = data["documents"]
                    self.metadatas = data["metadatas"]
                    tokenized_corpus = [self.tokenize(doc) for doc in self.documents]
                    self.bm25 = BM25Okapi(tokenized_corpus)
                logger.info(f"Loaded existing BM25 index with {len(self.documents)} chunks.")
            except Exception as e:
                logger.error(f"Failed to load BM25 index from {self.index_path}: {e}")
                self.bm25 = None

    def search(self, query: str, top_k: int = 10, source_filter: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Runs BM25 lexical scoring over the corpus.
        Returns ordered list of matches with bm25_rank and normalized score.
        """
        if "n_results" in kwargs:
            top_k = kwargs["n_results"]
        if not self.bm25 or not self.documents:
            return []

        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        scored_docs = []

        for idx, score in enumerate(scores):
            meta = self.metadatas[idx]
            if source_filter and source_filter.lower() in ["darglobal", "wasalt"]:
                expected = "DarGlobal" if source_filter.lower() == "darglobal" else "Wasalt"
                if meta.get("source") != expected:
                    continue

            if score > 0.0:
                scored_docs.append((idx, float(score)))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        max_score = scored_docs[0][1] if scored_docs else 1.0

        hits: List[Dict[str, Any]] = []
        for rank, (idx, score) in enumerate(scored_docs[:top_k]):
            hits.append({
                "chunk_id": self.chunk_ids[idx],
                "text": self.documents[idx],
                "metadata": self.metadatas[idx],
                "score": score / (max_score + 1e-6),  # normalized
                "raw_score": score,
                "bm25_rank": rank + 1
            })

        return hits

    def get_count(self) -> int:
        return len(self.documents)
