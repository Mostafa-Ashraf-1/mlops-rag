from legal_rag.schemas import ArticleRecord
from legal_rag.chunker import LegalArticleChunker

def test_chunk_article_single_and_multi():
    chunker = LegalArticleChunker(max_tokens=512)
    
    # Test single paragraph
    art1 = ArticleRecord(
        article_number=147,
        book="Obligations",
        chapter="Contracts",
        section="Effects",
        topic="General",
        text_ar="العقد شريعة المتعاقدين، فلا يجوز نقضه ولا تعديله.",
        text_en="The contract makes the law of the parties.",
        is_repealed=False,
        source_page=34,
        citation="Egyptian Civil Code, Article 147"
    )
    chunks1 = chunker.chunk_article(art1)
    assert len(chunks1) == 1
    assert chunks1[0].chunk_id == "art_147_p1"
    assert chunks1[0].citation == "Egyptian Civil Code, Article 147"

    # Test multi paragraph
    art2 = ArticleRecord(
        article_number=1,
        book="General",
        chapter="Laws",
        section="General",
        topic="General",
        text_ar="(١) تسري النصوص التشريعية. (٢) فإذا لم يوجد نص تشريعي حكم القاضي بالعرف.",
        text_en="Provisions of laws govern all matters.",
        is_repealed=False,
        source_page=1,
        citation="Egyptian Civil Code, Article 1"
    )
    chunks2 = chunker.chunk_article(art2)
    assert len(chunks2) == 2
    assert chunks2[0].chunk_id == "art_1_p1"
    assert chunks2[1].chunk_id == "art_1_p2"
    assert chunks2[1].paragraph_index == 2