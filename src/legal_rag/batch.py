import os
import time
import json
import psutil
from typing import List, Dict, Any
from pathlib import Path

from legal_rag.config import settings
from legal_rag.schemas import ArticleRecord, ArticleChunk
from legal_rag.chunker import LegalArticleChunker
from legal_rag.retriever import LegalRetriever


class BatchReindexer:
    """
    Offline batch re-indexing pipeline for new legal amendments and decrees.
    Processes documents in vectorized batches with resource and cost accounting.
    """

    def __init__(self, retriever: LegalRetriever = None):
        self.retriever = retriever or LegalRetriever()
        self.chunker = LegalArticleChunker()

    def reindex_amendments(self, amendment_file: Path) -> Dict[str, Any]:
        """Ingests, chunks, and batch-upserts new legal provisions into the vector store."""
        if not amendment_file.exists():
            raise FileNotFoundError(f"Amendment file not found at: {amendment_file}")

        process = psutil.Process(os.getpid())
        mem_before_mb = process.memory_info().rss / (1024 * 1024)
        start_time = time.perf_counter()

        with open(amendment_file, "r", encoding="utf-8") as f:
            raw_docs = json.load(f)

        articles = [ArticleRecord(**doc) for doc in raw_docs]

        new_chunks: List[ArticleChunk] = []
        for art in articles:
            chunks = self.chunker.chunk_article(art)
            new_chunks.extend(chunks)

        # Batch upsert to vector store
        self.retriever.index_chunks(new_chunks, batch_size=32, skip_existing=False)

        duration_sec = time.perf_counter() - start_time
        mem_after_mb = process.memory_info().rss / (1024 * 1024)
        peak_mem_mb = max(mem_after_mb - mem_before_mb, 0.0)
        throughput = len(new_chunks) / duration_sec if duration_sec > 0 else len(new_chunks)

        # Compute cost model (Cloud pricing: AWS c6i.xlarge 4vCPU @ $0.17/hr)
        cost_per_hour = 0.17
        instance_hours_per_chunk = (duration_sec / max(len(new_chunks), 1)) / 3600
        cost_per_million_chunks = instance_hours_per_chunk * 1_000_000 * cost_per_hour

        return {
            "articles_processed": len(articles),
            "chunks_indexed": len(new_chunks),
            "wall_clock_sec": round(duration_sec, 2),
            "peak_memory_mb": round(peak_mem_mb, 2),
            "throughput_chunks_per_sec": round(throughput, 2),
            "cost_per_million_predictions_usd": round(cost_per_million_chunks, 2),
            "total_collection_count": self.retriever.count(),
        }