import re
from typing import Dict, Any

from app.services.text_utils import normalize_text, split_bullets, unique_preserve_order
from app.services.skill_taxonomy import extract_skills_from_text, pretty_skill


def parse_job_description(job_text: str) -> Dict[str, Any]:
    text = normalize_text(job_text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else "Target Role"

    req_match = re.search(r"(?is)(required|requirements|must have)\s*[:\n](.*?)(?=\n(?:preferred|nice to have|responsibilities|what you'll do|about the role)|\Z)", text)
    pref_match = re.search(r"(?is)(preferred|nice to have)\s*[:\n](.*?)(?=\n(?:responsibilities|what you'll do|about the role)|\Z)", text)
    resp_match = re.search(r"(?is)(responsibilities|what you'll do|about the role)\s*[:\n](.*?)(?=\n(?:preferred|requirements|must have)|\Z)", text)

    required = split_bullets(req_match.group(2)) if req_match else []
    preferred = split_bullets(pref_match.group(2)) if pref_match else []
    responsibilities = split_bullets(resp_match.group(2)) if resp_match else []

    raw_skills = extract_skills_from_text(text)
    keywords = unique_preserve_order([pretty_skill(s) for s in raw_skills])

    return {
        "title": title,
        "required_skills": required or keywords,
        "preferred_skills": preferred,
        "responsibilities": responsibilities,
        "keywords": keywords,
    }