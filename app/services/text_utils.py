import re
from typing import List


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    # Remove LaTeX separators/entities leaking into plain text extraction.
    text = text.replace(r"\&", " and ")
    text = text.replace("&", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def tokenize_lower(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9\+\#\.\-]+", text.lower())


def unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


def split_bullets(text: str) -> List[str]:
    lines = [line.strip("-• ").strip() for line in text.splitlines()]
    return [line for line in lines if len(line) > 6]


def keyword_overlap_ratio(a_items: List[str], b_items: List[str]) -> float:
    a = {x.lower().strip() for x in a_items if x.strip()}
    b = {x.lower().strip() for x in b_items if x.strip()}
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))
