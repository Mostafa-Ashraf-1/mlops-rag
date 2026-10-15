from legal_rag.text_normalizer import (
    extract_article_number,
    fix_visual_arabic,
    normalize_arabic,
    normalize_digits,
    normalize_english,
)


def test_normalize_digits():
    assert normalize_digits("مادة ١٤٧") == "مادة 147"
    assert normalize_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"


def test_extract_article_number():
    assert extract_article_number("مادة ( ١٤٧ )") == 147
    assert extract_article_number("Article 147") == 147
    assert extract_article_number("Article 54") == 54
    assert extract_article_number("793 ةدام") == 793
    assert extract_article_number("نص عام بدون رقم") is None


def test_fix_visual_arabic():
    visual_ar = "793 ةدام\n.ديرجتلا بلطي نا نيدملا عم نماضتملا ليفكلل زوجي لا"
    fixed = fix_visual_arabic(visual_ar)
    assert "لا يجوز للكفيل المتضامن مع المدين" in fixed


def test_normalize_arabic():
    raw = "العَقْدُ   شَرِيعَةُ المُتَعَاقِدِينَ، إِذْ أَنَّهُـ..."
    normalized = normalize_arabic(raw)
    assert "َ" not in normalized  # No Tashkeel
    assert "ـ" not in normalized  # No Tatweel
    assert "ا" in normalized  # Normalized Alef
    assert normalize_arabic("") == ""


def test_normalize_english():
    raw = "The  contract   makes\n\n\nthe law."
    cleaned = normalize_english(raw)
    assert "  " not in cleaned
    assert "\n\n\n" not in cleaned
    assert normalize_english("") == ""
