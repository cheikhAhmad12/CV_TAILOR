import re
from typing import List, Dict, Any

from app.services.text_utils import normalize_text, unique_preserve_order
from app.services.skill_taxonomy import extract_skills_from_text, pretty_skill


SECTION_ALIASES = {
    "summary": ["summary", "profile", "professional summary"],
    "experience": ["experience", "work experience", "professional experience"],
    "skills": ["skills", "technical skills", "core skills"],
    "education": ["education", "academic background"],
    "projects": [
        "projects",
        "selected projects",
        "personal projects",
        "personal and academic projects",
        "projets",
        "projets selectionnes",
        "projets personnels et académiques",
        "projets personnels et academiques",
    ],
}


def _extract_experiences_from_latex(latex_source: str) -> List[Dict[str, str]]:
    if "\\resumeSubheading" not in latex_source:
        return []

    experiences: List[Dict[str, str]] = []
    pattern = re.compile(
        r"\\resumeSubheading\s*\{([^}]*)\}\{[^}]*\}\{([^}]*)\}\{([^}]*)\}",
        flags=re.DOTALL,
    )
    matches = list(pattern.finditer(latex_source))
    if not matches:
        return []

    for idx, match in enumerate(matches):
        company = normalize_text(match.group(1))
        title = normalize_text(match.group(2))
        date_range = normalize_text(match.group(3))

        block_start = match.end()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(latex_source)
        block = latex_source[block_start:block_end]

        bullets = re.findall(r"\\resumeItem\{([^}]*)\}", block, flags=re.DOTALL)
        bullet_text = " ".join(normalize_text(b) for b in bullets if normalize_text(b))
        description = f"{date_range}. {bullet_text}".strip(". ").strip()
        if not description:
            description = date_range

        if title or company or description:
            experiences.append(
                {
                    "title": title or company or "Experience",
                    "company": company,
                    "description": description,
                }
            )

    return experiences


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
    projects_block = _extract_section(text, SECTION_ALIASES["projects"])

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

    if not experiences:
        experiences = _extract_experiences_from_latex(master_cv_text)

    education = [line.strip() for line in education_block.splitlines() if line.strip()] if education_block else []
    projects = []
    if projects_block:
        for raw_line in projects_block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^[\-\*\u2022]+\s*", "", line).strip()
            if len(line) < 4:
                continue
            projects.append(line)
    projects = unique_preserve_order(projects)[:6]

    return {
        "summary": summary or "Technical candidate with relevant engineering and project experience.",
        "skills": skills,
        "experiences": experiences,
        "education": education,
        "projects": projects,
    }
