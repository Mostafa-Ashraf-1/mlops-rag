import re
import unicodedata
from typing import Optional

try:
    from bidi.algorithm import get_display
except (ImportError, ModuleNotFoundError):
    try:
        from bidi import get_display
    except (ImportError, ModuleNotFoundError):
        get_display = None

# Arabic-Indic to Western Digit translation
ARABIC_INDIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

# Regex for Arabic diacritics
TASHKEEL_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652\u0670]')


def normalize_digits(text: str) -> str:
    """Converts Arabic-Indic digits (١٤٧) to Western digits (147)."""
    return text.translate(ARABIC_INDIC_DIGITS)


def is_arabic_reversed(text: str) -> bool:
    """
    Detects if an Arabic text string is visually reversed (LTR extraction order).
    In standard Arabic:
    - No word ever starts with Taa Marbuta 'ة' (e.g. 'ةدام' or 'ةعيرش' means reversed).
    - Common reversed prepositions: 'يف' (في), 'ىلع' (على), 'ىلا' (الى).
    """
    if not text or not re.search(r"[\u0600-\u06FF]", text):
        return False

    # 1. Definitive indicator: words starting with 'ة'
    if re.search(r'\bة\w+', text):
        return True

    # 2. Marker frequency comparison
    reversed_markers = len(re.findall(r'\b(?:يف|ىلع|ىلا|ةدام|دقعلا|نوناقلا)\b', text))
    logical_markers = len(re.findall(r'\b(?:في|على|إلى|الى|مادة|العقد|القانون)\b', text))

    logical_al = len(re.findall(r'\bال\w{2,}', text))
    reversed_al = len(re.findall(r'\w{2,}لا\b', text))

    return (reversed_markers + reversed_al) > (logical_markers + logical_al)


def fix_visual_arabic(text: str) -> str:
    """
    Reorders visually reversed Arabic lines into logical RTL reading order.
    If the text is already in logical order, returns it untouched.
    """
    if not text or not text.strip():
        return ""

    # If text is already logical Arabic, do not reverse it!
    if not is_arabic_reversed(text):
        return text

    lines = text.split("\n")
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            fixed_lines.append("")
            continue

        if re.search(r"[\u0600-\u06FF]", stripped) and get_display:
            try:
                reordered = get_display(stripped, base_dir="R")
            except TypeError:
                reordered = get_display(stripped)
            except Exception:
                reordered = stripped

            # Fix Lam-Alef ligature inversions caused by BiDi on PDF text
            reordered = re.sub(r'\bال\b', 'لا', reordered)
            reordered = re.sub(r'\bوال\b', 'ولا', reordered)
            reordered = re.sub(r'\bفال\b', 'فلا', reordered)
            reordered = re.sub(r'\bاال\b', 'الا', reordered)
            reordered = re.sub(r'\bبال\b', 'بلا', reordered)

            fixed_lines.append(reordered)
        else:
            fixed_lines.append(stripped)

    return "\n".join(fixed_lines)


def extract_article_number(text: str) -> Optional[int]:
    """Extracts integer article number from Arabic or English heading."""
    if not text:
        return None
    normalized = normalize_digits(text)

    # 1. Match logical order: "مادة 147", "مادة (147)", "Article 147", "rticle 147"
    match = re.search(r'(?:مادة|A?rticle)\s*[\(\[]?\s*(\d+)\s*[\)\]]?', normalized, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # 2. Match reversed visual order: "147 ةدام", "( 147 ) ةدام"
    rev_match = re.search(r'[\(\[]?\s*(\d+)\s*[\)\]]?\s*ةدام', normalized)
    if rev_match:
        return int(rev_match.group(1))

    return None


def normalize_arabic(text: str) -> str:
    """
    Cleans raw Arabic text:
    - Removes Tashkeel (diacritics)
    - Removes Tatweel / Kashida (ـ)
    - Normalizes Alef variations (أ, إ, آ -> ا)
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
    return text.strip()