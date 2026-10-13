import json
import pytest
from pathlib import Path
from legal_rag.config import settings
from legal_rag.schemas import ArticleRecord

@pytest.fixture(scope="session")
def corpus_records():
    assert settings.PROCESSED_JSON_PATH.exists(), "Processed corpus JSON does not exist. Run parsing script first."
    with open(settings.PROCESSED_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [ArticleRecord(**item) for item in data]

def test_article_numbers_contiguous_no_gaps(corpus_records):
    """Asserts article numbers are contiguous from 1 to 1149 with no missing articles."""
    extracted_numbers = [r.article_number for r in corpus_records]
    expected_numbers = list(range(1, 1150))

    missing = set(expected_numbers) - set(extracted_numbers)
    assert not missing, f"Missing article numbers detected: {sorted(list(missing))[:10]}"
    assert extracted_numbers == expected_numbers, "Articles are not in strictly sequential order"

def test_every_record_has_non_empty_text_ar(corpus_records):
    """Asserts no article has blank or whitespace-only Arabic text."""
    for record in corpus_records:
        assert record.text_ar is not None
        assert len(record.text_ar.strip()) >= 5, f"Article {record.article_number} has empty text"

def test_no_record_exceeds_sane_length(corpus_records):
    """Asserts no article exceeds maximum threshold (catches bad splits)."""
    for record in corpus_records:
        assert len(record.text_ar) < 15000, f"Article {record.article_number} exceeded length: {len(record.text_ar)}"

def test_repealed_articles_properly_flagged(corpus_records):
    """Asserts Articles 54 through 80 and 389 through 417 are marked is_repealed=True."""
    repealed_range = set(range(54, 81)) | set(range(389, 418))
    for record in corpus_records:
        if record.article_number in repealed_range:
            assert record.is_repealed is True, f"Article {record.article_number} must be marked is_repealed=True"
            assert "ألغيت" in record.text_ar or "repealed" in record.text_en.lower()
        else:
            assert record.is_repealed is False, f"Article {record.article_number} was incorrectly flagged as repealed"

def test_citation_format(corpus_records):
    """Asserts citation strings strictly follow the standard."""
    for record in corpus_records:
        assert record.citation.startswith("Egyptian Civil Code, Article ")
        assert str(record.article_number) in record.citation