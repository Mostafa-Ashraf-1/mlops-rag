## File: src/legal_rag/schemas.py
```
from typing import Optional, List
from pydantic import BaseModel, Field

class ArticleRecord(BaseModel):
    article_number: int = Field(..., ge=1, le=1200, description="Normalized integer article number")
    book: str = Field(..., description="Top-level hierarchy: Book (الكتاب)")
    chapter: str = Field(..., description="Chapter hierarchy: Chapter (الباب)")
    section: str = Field(..., description="Section hierarchy: Section (الفصل)")
    topic: str = Field(..., description="Specific subtopic or heading")
    text_ar: str = Field(..., min_length=5, description="Normalized Arabic article text")
    text_en: str = Field(..., min_length=5, description="Normalized English article text")
    is_repealed: bool = Field(default=False, description="Whether this article has been repealed")
    source_page: int = Field(..., ge=1, description="Original page number in source PDF")
    citation: str = Field(..., description="Formal legal citation string")

class ArticleChunk(BaseModel):
    chunk_id: str
    article_number: int
    citation: str
    book: str
    chapter: str
    section: str
    topic: str
    text_ar: str
    text_en: str
    paragraph_index: int = 0
    total_paragraphs: int = 1
    is_repealed: bool = False

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        json_schema_extra={"example": "ما هي شروط العقد وما هو الغبن؟"}
    )
    top_k: int = Field(default=3, ge=1, le=10)

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[str] = Field(..., description="Legal citations, strictly article numbers")
    model_version: str
    correlation_id: str
    latency_ms: float```

## File: src/legal_rag/text_normalizer.py
```
import re
import unicodedata
from typing import Optional

# Arabic-Indic to Western Digit translation
ARABIC_INDIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

# Regex for Arabic diacritics (Tashkeel: Fatha, Damma, Kasra, Sukun, Tanwin, Shadda, etc.)
TASHKEEL_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652\u0670]')

def normalize_digits(text: str) -> str:
    """Converts Arabic-Indic digits (١٤٧) to Western digits (147)."""
    return text.translate(ARABIC_INDIC_DIGITS)

def extract_article_number(text: str) -> Optional[int]:
    """Extracts integer article number from Arabic or English heading."""
    normalized = normalize_digits(text)
    match = re.search(r'(?:مادة|Article)\s*[\(\[]?\s*(\d+)\s*[\)\]]?', normalized, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def normalize_arabic(text: str) -> str:
    """
    Cleans raw Arabic text:
    - Removes Tashkeel (diacritics)
    - Removes Tatweel / Kashida (ـ)
    - Normalizes Alef variations (أ, إ, آ -> ا)
    - Normalizes Alef Maksura (ى -> ي) and Taa Marbuta (ة -> ه) where appropriate
    - Unifies Unicode whitespaces
    """
    if not text:
        return ""
    
    text = unicodedata.normalize('NFKC', text)
    text = normalize_digits(text)
    
    # Remove Tatweel
    text = re.sub(r'\u0640', '', text)
    
    # Strip Tashkeel
    text = TASHKEEL_REGEX.sub('', text)
    
    # Normalize Alef forms
    text = re.sub(r'[إأآٱ]', 'ا', text)
    
    # Normalize excessive spaces and linebreaks
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def normalize_english(text: str) -> str:
    """Normalizes English legal text."""
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()```

## File: src/legal_rag/config.py
```
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Egyptian Civil Code Legal RAG"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DATA_DIR: Path = Path("data")
    RAW_PDF_PATH: Path = Path("data/raw/egyptian_civil_code.pdf")
    PROCESSED_JSON_PATH: Path = Path("data/processed/egyptian_civil_code.json")
    CHUNKS_JSON_PATH: Path = Path("data/processed/chunks.json")

settings = Settings()```

## File: src/legal_rag/__init__.py
```
```

## File: src/legal_rag/parser.py
```
import re
from typing import List, Dict, Optional
import pdfplumber
from legal_rag.schemas import ArticleRecord
from legal_rag.text_normalizer import (
    normalize_arabic,
    normalize_english,
    extract_article_number
)

REPEALED_RANGES = {
    (54, 80): {
        "topic": "Associations and Foundations / الجمعيات والمؤسسات",
        "text_ar": "ألغيت المواد من 54 إلى 80 بالقرار الجمهوري بالقانون رقم 348 لسنة 1956 ثم ألغي بالقرار الجمهوري رقم 32 لسنة 1964.",
        "text_en": "Articles 54 to 80 have been repealed by Presidential Decree Law No. 348 of 1956, subsequently repealed by Presidential Decree No. 32 of 1964.",
        "book": "General Provisions / أحكام عامة",
        "chapter": "Persons / الأشخاص",
        "section": "Juristic Persons / الأشخاص الاعتبارية",
    },
    (389, 417): {
        "topic": "Proof of Obligations / إثبات الالتزام",
        "text_ar": "ألغيت المواد من 389 إلى 417 بموجب قانون الإثبات في المواد المدنية والتجارية رقم 25 لسنة 1968.",
        "text_en": "Articles 389 to 417 have been repealed by Law No. 25 of 1968 (Law of Evidence in Civil and Commercial Matters).",
        "book": "Obligations Generally / الالتزامات بوجه عام",
        "chapter": "Proof of Obligations / إثبات الالتزام",
        "section": "Proof / الإثبات",
    }
}

class CivilCodeParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.current_book = "General Provisions / أحكام عامة"
        self.current_chapter = "Sources of Law / مصادر القانون"
        self.current_section = "General / عام"
        self.current_topic = "General Provisions / أحكام عامة"

    def _is_hierarchy_heading(self, text_ar: str, text_en: str):
        norm_ar = text_ar.strip()
        norm_en = text_en.strip()

        if "الكتاب" in norm_ar or "BOOK" in norm_en.upper():
            self.current_book = norm_en or norm_ar
        elif "الباب" in norm_ar or "CHAPTER" in norm_en.upper():
            self.current_chapter = norm_en or norm_ar
        elif "الفصل" in norm_ar or "SECTION" in norm_en.upper():
            self.current_section = norm_en or norm_ar
        elif any(k in norm_ar for k in ["أولا", "ثانيا", "ثالثا", "١-", "٢-"]):
            self.current_topic = norm_en or norm_ar

    def _inject_repealed_range(self, articles: Dict[int, ArticleRecord], start: int, end: int, page_num: int):
        meta = REPEALED_RANGES.get((start, end))
        if not meta:
            return
        for num in range(start, end + 1):
            articles[num] = ArticleRecord(
                article_number=num,
                book=meta["book"],
                chapter=meta["chapter"],
                section=meta["section"],
                topic=meta["topic"],
                text_ar=meta["text_ar"],
                text_en=meta["text_en"],
                is_repealed=True,
                source_page=page_num,
                citation=f"Egyptian Civil Code, Article {num} (Repealed)"
            )

    def parse(self) -> List[ArticleRecord]:
        articles: Dict[int, ArticleRecord] = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                page_text = page.extract_text() or ""

                # Check for repealed ranges
                if any(k in page_text for k in ["54-80", "٥٤ إلى ٨٠", "54 إلى 80"]):
                    self._inject_repealed_range(articles, 54, 80, page_num)

                if any(k in page_text for k in ["389-417", "٣٨٩ إلى ٤١٧", "389 إلى 417"]):
                    self._inject_repealed_range(articles, 389, 417, page_num)

                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row or len(row) < 2:
                                continue
                            col_en = row[0] or ""
                            col_ar = row[1] or ""
                            self._process_row(col_ar, col_en, page_num, articles)

        # Safety fill for repealed blocks if missed by regex
        if 54 not in articles or not articles[54].is_repealed:
            self._inject_repealed_range(articles, 54, 80, 7)
        if 389 not in articles or not articles[389].is_repealed:
            self._inject_repealed_range(articles, 389, 417, 53)

        return sorted(articles.values(), key=lambda x: x.article_number)

    def _process_row(self, col_ar: str, col_en: str, page_num: int, articles: Dict[int, ArticleRecord]):
        art_num = extract_article_number(col_ar) or extract_article_number(col_en)

        # Do not overwrite articles that fall into the known repealed ranges
        if art_num and (54 <= art_num <= 80 or 389 <= art_num <= 417):
            return

        if art_num:
            clean_ar = re.sub(r'^.*?مادة\s*[\(\[]?\s*[0-9٠-٩]+\s*[\)\]]?', '', col_ar, flags=re.DOTALL)
            clean_en = re.sub(r'^.*?Article\s*[0-9]+\s*', '', col_en, flags=re.DOTALL | re.IGNORECASE)

            clean_ar = normalize_arabic(clean_ar)
            clean_en = normalize_english(clean_en)

            if clean_ar:
                articles[art_num] = ArticleRecord(
                    article_number=art_num,
                    book=self.current_book,
                    chapter=self.current_chapter,
                    section=self.current_section,
                    topic=self.current_topic,
                    text_ar=clean_ar,
                    text_en=clean_en or clean_ar,
                    is_repealed=False,
                    source_page=page_num,
                    citation=f"Egyptian Civil Code, Article {art_num}"
                )
        else:
            self._is_hierarchy_heading(col_ar, col_en)```

## File: src/legal_rag/api/__init__.py
```
```

## File: src/legal_rag/api/main.py
```
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from legal_rag.config import settings
from legal_rag.schemas import AskRequest, AskResponse, ArticleRecord
from legal_rag.text_normalizer import normalize_arabic

# In-memory document storage loaded at startup
CORPUS_STORE: Dict[int, ArticleRecord] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup lifespan context manager to load corpus into memory once."""
    if settings.PROCESSED_JSON_PATH.exists():
        with open(settings.PROCESSED_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                record = ArticleRecord(**item)
                CORPUS_STORE[record.article_number] = record
        print(f"[API Startup] Loaded {len(CORPUS_STORE)} legal articles into memory.")
    else:
        print("[API Warning] Corpus file not found on startup! /health will return 503.")
    yield
    CORPUS_STORE.clear()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    start_time = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = correlation_id
    response.headers["X-Response-Time-MS"] = f"{latency_ms:.2f}"
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error in request payload", "errors": exc.errors()}
    )

@app.get("/health", status_code=status.HTTP_200_OK)
async def health():
    if not CORPUS_STORE:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "unhealthy", "reason": "Corpus not loaded"})
    return {"status": "healthy", "articles_loaded": len(CORPUS_STORE)}

@app.get("/metadata")
async def metadata():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "total_articles": len(CORPUS_STORE),
        "language": "bilingual (ar/en)",
        "jurisdiction": "Egypt (Law of 1948)"
    }

@app.post("/ask", response_model=AskResponse)
async def ask(request: Request, payload: AskRequest):
    start = time.perf_counter()
    cleaned_query = normalize_arabic(payload.question)
    
    # Exact / heuristic legal matching fallback before vector embedding phase
    matched_articles: List[ArticleRecord] = []
    
    # Keyword & article matching logic
    for art in CORPUS_STORE.values():
        if cleaned_query in art.text_ar or any(word in art.text_ar for word in cleaned_query.split() if len(word) > 3):
            matched_articles.append(art)
        if len(matched_articles) >= payload.top_k:
            break
            
    if not matched_articles and CORPUS_STORE:
        matched_articles = [CORPUS_STORE[147]]  # Default canonical fallback (Article 147)

    sources = [art.citation for art in matched_articles]
    combined_context = "\n\n".join([f"[{a.citation}]: {a.text_ar}" for a in matched_articles])
    
    answer = f"بناءً على أحكام القانون المدني المصري:\n{combined_context}"
    latency = (time.perf_counter() - start) * 1000
    
    return AskResponse(
        question=payload.question,
        answer=answer,
        sources=sources,
        model_version="corpus-v1-baseline",
        correlation_id=request.state.correlation_id,
        latency_ms=round(latency, 2)
    )```

## File: src/legal_rag/retriever.py
```
```

## File: src/legal_rag/chunker.py
```
import re
from typing import List
from legal_rag.schemas import ArticleRecord, ArticleChunk

class LegalArticleChunker:
    def __init__(self, max_tokens: int = 512):
        self.max_tokens = max_tokens

    def chunk_article(self, article: ArticleRecord) -> List[ArticleChunk]:
        """
        Chunks an article respecting provision boundaries.
        Never cuts mid-sentence or mid-provision.
        """
        # Split on paragraph markers: (1), (2) or (١), (٢)
        paragraphs = re.split(r'(?=\([0-9٠-٩]+\))', article.text_ar)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            paragraphs = [article.text_ar]
            
        chunks = []
        total_p = len(paragraphs)
        
        for idx, para in enumerate(paragraphs):
            chunk_id = f"art_{article.article_number}_p{idx+1}"
            chunks.append(
                ArticleChunk(
                    chunk_id=chunk_id,
                    article_number=article.article_number,
                    citation=article.citation,
                    book=article.book,
                    chapter=article.chapter,
                    section=article.section,
                    topic=article.topic,
                    text_ar=para,
                    text_en=article.text_en,
                    paragraph_index=idx + 1,
                    total_paragraphs=total_p,
                    is_repealed=article.is_repealed
                )
            )
        return chunks```

