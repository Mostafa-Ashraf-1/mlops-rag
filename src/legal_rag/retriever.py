from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm
import chromadb
from sentence_transformers import SentenceTransformer
from legal_rag.config import settings
from legal_rag.schemas import ArticleChunk


class LegalRetriever:
    """
    Production ChromaDB Vector Retriever using Qwen3-Embedding-0.6B for
    dense multilingual legal text search across the Egyptian Civil Code.
    """

    def __init__(
        self,
        persist_directory: Path = settings.CHROMA_DB_DIR,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
        model_name: str = settings.EMBEDDING_MODEL_NAME,
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.model_name = model_name

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy loader for SentenceTransformer to allow fast startup and lightweight unit testing."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates normalized vector embeddings using Qwen3-Embedding-0.6B."""
        if not texts:
            return []
        import torch
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return embeddings

    def index_chunks(self, chunks: List[ArticleChunk], batch_size: int = 64, skip_existing: bool = True):
        """Indexes legal chunks into ChromaDB with a real-time visual progress bar and resume support."""
        if not chunks:
            return

        if skip_existing:
            existing_ids = set(self.collection.get(include=[])["ids"])
            chunks_to_index = [c for c in chunks if c.chunk_id not in existing_ids]
        else:
            chunks_to_index = chunks

        total_to_index = len(chunks_to_index)
        if total_to_index == 0:
            print(f"[✓] All {len(chunks)} chunks are already indexed in ChromaDB.", flush=True)
            return

        skipped = len(chunks) - total_to_index
        print(f"[*] Resuming: indexing {total_to_index} remaining chunks ({skipped} already cached in ChromaDB)...", flush=True)

        with tqdm(total=total_to_index, desc="Indexing legal chunks", unit="chunk", dynamic_ncols=True) as pbar:
            for i in range(0, total_to_index, batch_size):
                batch = chunks_to_index[i:i + batch_size]
                ids = [c.chunk_id for c in batch]
                documents = [c.text_ar for c in batch]
                metadatas = [
                    {
                        "article_number": c.article_number,
                        "paragraph_index": c.paragraph_index if c.paragraph_index is not None else 0,
                        "total_paragraphs": c.total_paragraphs,
                        "book": c.book or "",
                        "chapter": c.chapter or "",
                        "section": c.section or "",
                        "topic": c.topic or "",
                        "citation": c.citation,
                        "is_repealed": c.is_repealed,
                    }
                    for c in batch
                ]
                embeddings = self.embed_texts(documents)

                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                )
                pbar.update(len(batch))

        print(f"[✓] Done! Total chunks in ChromaDB: {self.collection.count()}", flush=True)

    def search(
        self,
        query: str,
        top_k: int = 3,
        filter_repealed: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Executes dense semantic similarity search against the legal corpus.
        Returns matched documents with citations and similarity scores.
        """
        if not query or self.collection.count() == 0:
            return []

        query_embedding = self.embed_texts([query])
        where_filter = {"is_repealed": False} if filter_repealed else None

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self.collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        hits: List[Dict[str, Any]] = []
        if results and results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                distance = results["distances"][0][idx] if results.get("distances") else 0.0
                score = round(float(1.0 - distance), 4)

                hits.append({
                    "chunk_id": results["ids"][0][idx],
                    "document": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx],
                    "score": score,
                })

        return hits

    def count(self) -> int:
        """Returns the number of indexed documents in the collection."""
        return self.collection.count()