from unittest.mock import MagicMock, patch
from legal_rag.parser import CivilCodeParser


def test_parser_hierarchy_headings():
    parser = CivilCodeParser("dummy.pdf")
    parser._is_hierarchy_heading("الكتاب الأول - الالتزامات", "BOOK I - OBLIGATIONS")
    assert "BOOK I" in parser.current_book
    parser._is_hierarchy_heading("الباب الأول - مصادر الالتزام", "CHAPTER I")
    assert "CHAPTER I" in parser.current_chapter
    parser._is_hierarchy_heading("الفصل الأول - العقد", "SECTION I")
    assert "SECTION I" in parser.current_section


def test_parser_inject_repealed():
    parser = CivilCodeParser("dummy.pdf")
    articles = {}
    parser._inject_repealed_range(articles, 54, 80, 7)
    assert len(articles) == 27
    assert 54 in articles
    assert 80 in articles
    assert articles[54].is_repealed is True


def test_parser_process_row_basic():
    parser = CivilCodeParser("dummy.pdf")
    raw_articles = {}
    parser._process_row(
        col_ar="مادة 147\nالعقد شريعة المتعاقدين",
        col_en="Article 147\nThe contract makes the law",
        page_num=16,
        raw_articles=raw_articles,
    )
    assert 147 in raw_articles
    assert "العقد شريعة المتعاقدين" in raw_articles[147]["text_ar"]


def test_parser_process_row_continuation():
    parser = CivilCodeParser("dummy.pdf")
    raw_articles = {}
    # Row 1: Header only
    parser._process_row(
        col_ar="مادة 120",
        col_en="Article 120",
        page_num=12,
        raw_articles=raw_articles,
    )
    assert 120 in raw_articles
    # Row 2: Continuation text
    parser._process_row(
        col_ar="إذا وقع المتعاقد في غلط جوهري",
        col_en="A party to a contract may demand avoidance",
        page_num=13,
        raw_articles=raw_articles,
    )
    assert "وقع المتعاقد" in raw_articles[120]["text_ar"]


def test_parser_process_row_repealed_skip():
    parser = CivilCodeParser("dummy.pdf")
    raw_articles = {}
    parser._process_row(
        col_ar="مادة 60",
        col_en="Article 60",
        page_num=7,
        raw_articles=raw_articles,
    )
    # Repealed articles in (54, 80) must be skipped during row processing
    assert 60 not in raw_articles


def test_parser_parse_mocked():
    parser = CivilCodeParser("dummy.pdf")
    mock_page = MagicMock()
    mock_page.extract_tables.return_value = [
        [
            [
                "Article 100\nAcceptance in adhesion contracts",
                "مادة 100\nالقبول في عقود الإذعان",
            ],
            ["SECTION II", "الفصل الثاني"],
        ]
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf
        records = parser.parse()
        assert len(records) > 0
        art100 = next(r for r in records if r.article_number == 100)
        assert art100.article_number == 100
        assert "القبول" in art100.text_ar