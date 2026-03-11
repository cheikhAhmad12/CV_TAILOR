from typing import Dict, Any, List


def compute_compatibility_score(parsed_cv: Dict[str, Any], parsed_job: Dict[str, Any], selected_projects: List[Dict[str, Any]]) -> float:
    cv_skills = {s.lower() for s in parsed_cv["skills"]}
    job_keywords = {s.lower() for s in parsed_job["keywords"]}

    skill_overlap = 0.0
    if job_keywords:
        skill_overlap = len(cv_skills.intersection(job_keywords)) / len(job_keywords)

    experience_count = len(parsed_cv["experiences"])
    experience_score = min(experience_count / 3, 1.0)

    project_score = 0.0
    if selected_projects:
        project_score = sum(p["score"] for p in selected_projects) / (len(selected_projects) * 100.0)

    keyword_coverage = skill_overlap

    final_score = (
        0.35 * skill_overlap
        + 0.25 * experience_score
        + 0.25 * project_score
        + 0.15 * keyword_coverage
    ) * 100

    return round(final_score, 2)


def compute_ats_score(resume_markdown: str, parsed_job: Dict[str, Any]) -> float:
    text = resume_markdown.lower()
    keywords = [k.lower() for k in parsed_job["keywords"]]

    keyword_hits = sum(1 for kw in keywords if kw in text)
    keyword_score = keyword_hits / max(len(keywords), 1)

    section_hits = 0
    for section in ["professional summary", "core skills", "professional experience", "education"]:
        if section in text:
            section_hits += 1
    section_score = section_hits / 4

    bullet_count = sum(1 for line in resume_markdown.splitlines() if line.strip().startswith("- "))
    bullet_score = min(bullet_count / 6, 1.0)

    score = (
        0.45 * keyword_score
        + 0.30 * section_score
        + 0.25 * bullet_score
    ) * 100

    return round(score, 2)