import json

import pytest

from legal_rag.config import settings
from legal_rag.schemas import ArticleRecord


@pytest.fixture(scope="module")
def corpus_records():
    """Loads the parsed legal corpus from disk, skipping if DVC data is not pulled."""
    json_path = settings.PROCESSED_JSON_PATH
    if not json_path.exists():
        pytest.skip(f"Processed corpus not found at {json_path} (DVC managed). Run dvc pull first.")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [ArticleRecord(**item) for item in data]


def test_article_numbers_contiguous_no_gaps(corpus_records):
    """Asserts article numbers are contiguous from 1 to 1149 with no missing articles."""
    extracted_numbers = [r.article_number for r in corpus_records]
    expected_numbers = list(range(1, 1150))

    missing = set(expected_numbers) - set(extracted_numbers)
    assert not missing, f"Missing article numbers detected: {sorted(missing)[:10]}"
    assert extracted_numbers == expected_numbers, "Articles are not in strictly sequential order"


def test_every_record_has_non_empty_text_ar(corpus_records):
    """Asserts no article has an empty Arabic text field."""
    for record in corpus_records:
        assert (
            record.text_ar and len(record.text_ar.strip()) > 0
        ), f"Article {record.article_number} has empty text_ar"


def test_no_record_exceeds_sane_length(corpus_records):
    """Asserts no article text exceeds 20,000 characters."""
    for record in corpus_records:
        assert (
            len(record.text_ar) < 20000
        ), f"Article {record.article_number} exceeds sane length ({len(record.text_ar)} chars)"


def test_repealed_articles_properly_flagged(corpus_records):
    """Asserts Articles 54 through 80 and 389 through 417 are marked is_repealed=True."""
    repealed_range = set(range(54, 81)) | set(range(389, 418))
    for record in corpus_records:
        if record.article_number in repealed_range:
            assert (
                record.is_repealed is True
            ), f"Article {record.article_number} must be marked is_repealed=True"
            assert "ألغيت" in record.text_ar or "repealed" in record.text_en.lower()
        else:
            assert (
                record.is_repealed is False
            ), f"Article {record.article_number} was incorrectly flagged as repealed"


def test_citation_format(corpus_records):
    """Asserts all citations follow the required format."""
    for record in corpus_records:
        if record.is_repealed:
            assert (
                record.citation
                == f"Egyptian Civil Code, Article {record.article_number} (Repealed)"
            )
        else:
            assert record.citation == f"Egyptian Civil Code, Article {record.article_number}"
