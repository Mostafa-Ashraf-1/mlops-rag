from unittest.mock import MagicMock

import pytest

from legal_rag.retriever import LegalRetriever
from legal_rag.schemas import ArticleChunk


@pytest.fixture
def mock_retriever(tmp_path):
    retriever = LegalRetriever(
        persist_directory=tmp_path / "chroma",
        collection_name="test_collection",
        model_name="dummy-model",
    )
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1] * 128]
    retriever._model = mock_model
    return retriever


def test_retriever_index_and_search(mock_retriever):
    chunk = ArticleChunk(
        chunk_id="art_147_p_1",
        article_number=147,
        paragraph_index=1,
        total_paragraphs=1,
        book="Obligations",
        chapter="Contracts",
        section="Effects",
        topic="General",
        text_ar="العقد شريعة المتعاقدين",
        text_en="The contract makes the law",
        is_repealed=False,
        source_page=16,
        citation="Egyptian Civil Code, Article 147",
    )

    mock_retriever.index_chunks([chunk])
    assert mock_retriever.count() == 1

    hits = mock_retriever.search("ما هو حكم العقد؟", top_k=1)
    assert len(hits) == 1
    assert hits[0]["metadata"]["article_number"] == 147
    assert hits[0]["metadata"]["citation"] == "Egyptian Civil Code, Article 147"
    assert "العقد شريعة المتعاقدين" in hits[0]["document"]


def test_retriever_empty_search(mock_retriever):
    hits = mock_retriever.search("", top_k=3)
    assert hits == []
