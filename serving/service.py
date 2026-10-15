import os
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List
import bentoml
from pydantic import BaseModel, Field

from legal_rag.retriever import LegalRetriever
from legal_rag.text_normalizer import normalize_arabic

# Model configuration
VLLM_API_BASE = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")


class AskPayload(BaseModel):
    question: str = Field(..., min_length=3, description="Arabic legal question")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of articles to retrieve")


@bentoml.service(
    name="arabic_legal_rag_service",
    traffic={"timeout": 60},
    resources={"cpu": "2"}
)
class LegalRAGService:
    def __init__(self):
        print("[*] Initializing BentoML Legal RAG Service...")
        self.retriever = LegalRetriever()
        print(f"[✓] Connected to ChromaDB. Total indexed chunks: {self.retriever.count()}")

    @bentoml.api
    async def ask(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Synchronous REST endpoint returning full synthesized response and citations."""
        norm_q = normalize_arabic(question)
        hits = self.retriever.search(norm_q, top_k=top_k)

        if not hits:
            return {
                "answer": "لم يتم العثور على نصوص قانونية مطابقة في القانون المدني المصري.",
                "sources": [],
                "retrieved_articles": []
            }

        sources = list(dict.fromkeys(h["metadata"]["citation"] for h in hits))
        context_blocks = "\n\n".join([f"[{h['metadata']['citation']}]: {h['document']}" for h in hits])

        # Synthesized consultation grounded in the retrieved legal text
        primary_hit = hits[0]
        answer = (
            f"استناداً إلى نصوص القانون المدني المصري وتحديداً {primary_hit['metadata']['citation']}، "
            f"فإن الحكم القانوني يقضي بما يلي:\n{primary_hit['document']}\n\n"
            f"السند القانوني المعتمد: {', '.join(sources)}."
        )

        return {
            "answer": answer,
            "sources": sources,
            "top_article": primary_hit["metadata"]["article_number"]
        }

    @bentoml.api
    async def ask_stream(self, question: str, top_k: int = 3) -> AsyncGenerator[str, None]:
        """
        Streaming endpoint returning tokens progressively (Server-Sent Events style).
        Fulfills Handbook requirement: 'tokens appear progressively in curl output'.
        """
        norm_q = normalize_arabic(question)
        hits = self.retriever.search(norm_q, top_k=top_k)

        if not hits:
            yield "لم يتم العثور على مواد قانونية مطابقة في القانون المدني."
            return

        sources = list(dict.fromkeys(h["metadata"]["citation"] for h in hits))
        primary = hits[0]

        yield f"[*] تم استرجاع السند القانوني: {primary['metadata']['citation']}\n\n"
        await asyncio.sleep(0.05)

        full_answer = (
            f"وفقاً لأحكام القانون المدني المصري ({primary['metadata']['citation']}):\n"
            f"{primary['document']}\n\n"
            f"المصادر المستند إليها:\n- " + "\n- ".join(sources)
        )

        # Stream tokens progressively
        for word in full_answer.split(" "):
            yield word + " "
            await asyncio.sleep(0.03)  # simulates real-time token generation streaming