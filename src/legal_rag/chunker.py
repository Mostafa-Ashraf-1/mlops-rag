import re

from legal_rag.schemas import ArticleChunk, ArticleRecord


class LegalArticleChunker:
    """
    Chunks legal articles respecting provision boundaries.
    Never splits across article boundaries or mid-sentence.
    """

    def __init__(self, max_tokens: int = 512):
        self.max_tokens = max_tokens

    def chunk_article(self, article: ArticleRecord) -> list[ArticleChunk]:
        """
        Chunks an article respecting provision boundaries.
        Never cuts mid-sentence or mid-provision.
        """
        # Split on paragraph markers: (1), (2) or (١), (٢)
        paragraphs = re.split(r"(?=\([0-9٠-٩]+\))", article.text_ar)
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
                    is_repealed=article.is_repealed,
                    source_page=article.source_page,
                )
            )

        return chunks
