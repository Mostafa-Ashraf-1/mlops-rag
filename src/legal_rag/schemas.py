from pydantic import BaseModel, Field


class ArticleRecord(BaseModel):
    article_number: int = Field(..., ge=1, le=1149, description="Sequential article number")
    book: str | None = Field(default=None, description="Book title hierarchy")
    chapter: str | None = Field(default=None, description="Chapter title hierarchy")
    section: str | None = Field(default=None, description="Section title hierarchy")
    topic: str | None = Field(default=None, description="Topic or subtopic")
    text_ar: str = Field(..., min_length=5, description="Normalized Arabic article text")
    text_en: str = Field(..., min_length=5, description="Normalized English article text")
    is_repealed: bool = Field(default=False, description="Whether the article has been repealed")
    source_page: int = Field(..., ge=1, description="Page number in original PDF")
    citation: str = Field(..., description="Canonical citation format")


class ArticleChunk(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk identifier e.g. art_147_p_1")
    article_number: int = Field(..., description="Referenced article number")
    paragraph_index: int | None = Field(
        default=None, description="Index of paragraph within article"
    )
    total_paragraphs: int = Field(default=1, description="Total paragraphs in this article")
    book: str | None = None
    chapter: str | None = None
    section: str | None = None
    topic: str | None = None
    text_ar: str = Field(..., description="Arabic text of the chunk")
    text_en: str = Field(..., description="English text of the chunk")
    is_repealed: bool = False
    source_page: int
    citation: str


class HealthResponse(BaseModel):
    status: str
    articles_loaded: int = Field(default=0, description="Total articles in memory")
    documents_indexed: int = Field(default=0, description="Total chunks indexed in vector store")


class MetadataResponse(BaseModel):
    project_name: str
    version: str
    total_articles: int
    law_name: str
    framework: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Legal question to ask")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of articles to retrieve")


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    correlation_id: str
    latency_ms: float
