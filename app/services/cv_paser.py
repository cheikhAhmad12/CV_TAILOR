import re
from typing import List, Dict, Any

from app.services.text_utils import normalize_text, unique_preserve_order
from app.services.skill_taxonomy import extract_skills_from_text, pretty_skill


SECTION_ALIASES = {
    "summary": ["summary", "profile", "professional summary"],
    "experience": ["experience", "work experience", "professional experience"],
    "skills": ["skills", "technical skills", "core skills"],
    "education": ["education", "academic background"],
}


def _extract_section(text: str, aliases: List[str]) -> str:
    all_headers = [h for vals in SECTION_ALIASES.values() for h in vals]
    alias_pattern = "|".join(re.escape(a) for a in aliases)
    all_pattern = "|".join(re.escape(a) for a in all_headers)
    pattern = rf"(?is)(?:^|\n)\s*(?:{alias_pattern})\s*[:\n](.*?)(?=\n\s*(?:{all_pattern})\s*[:\n]|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def parse_cv(master_cv_text: str) -> Dict[str, Any]:
    text = normalize_text(master_cv_text)

    summary = _extract_section(text, SECTION_ALIASES["summary"])
    exp_block = _extract_section(text, SECTION_ALIASES["experience"])
    skills_block = _extract_section(text, SECTION_ALIASES["skills"])
    education_block = _extract_section(text, SECTION_ALIASES["education"])

    inferred_skills = extract_skills_from_text(text)
    explicit_skills = re.split(r"[,|\n]", skills_block) if skills_block else []
    explicit_skills = [s.strip() for s in explicit_skills if s.strip()]
    skills = unique_preserve_order([pretty_skill(s) for s in inferred_skills] + explicit_skills)

    experiences = []
    if exp_block:
        chunks = [c.strip() for c in exp_block.split("\n\n") if c.strip()]
        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0]
            company = ""
            if " at " in lines[0].lower():
                parts = re.split(r"\s+at\s+", lines[0], flags=re.IGNORECASE)
                title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else ""
            description = " ".join(lines[1:]) if len(lines) > 1 else lines[0]
            experiences.append(
                {
                    "title": title,
                    "company": company,
                    "description": description,
                }
            )

    education = [line.strip() for line in education_block.splitlines() if line.strip()] if education_block else []

    return {
        "summary": summary or "Technical candidate with relevant engineering and project experience.",
        "skills": skills,
        "experiences": experiences,
        "education": education,
    }