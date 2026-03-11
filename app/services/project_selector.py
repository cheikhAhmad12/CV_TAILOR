from typing import List, Dict, Any

from app.schemas.github import GithubProject


def _simple_text(text: str) -> str:
    return text.lower().strip()


def _score_project(project: GithubProject, parsed_job: Dict[str, Any]) -> tuple[float, str]:
    job_text = " ".join(
        [parsed_job["title"]]
        + parsed_job["required_skills"]
        + parsed_job["preferred_skills"]
        + parsed_job["responsibilities"]
        + parsed_job["keywords"]
    ).lower()

    project_text = " ".join(
        [
            project.name,
            project.description,
            project.readme_summary,
            " ".join(project.languages),
            " ".join(project.topics),
        ]
    ).lower()

    job_keywords = {x.lower() for x in parsed_job["keywords"]}
    req_keywords = {x.lower() for x in parsed_job["required_skills"]}
    proj_tokens = set(project_text.split())

    keyword_hits = sum(1 for kw in job_keywords if kw in project_text)
    required_hits = sum(1 for kw in req_keywords if kw in project_text)

    topic_bonus = 0.0
    for t in project.topics:
        if t.lower() in {"llm", "rag", "nlp", "fastapi", "docker", "pytorch"}:
            topic_bonus += 0.05

    description_bonus = 0.1 if len(project.description.strip()) > 20 else 0.0
    readme_bonus = 0.1 if len(project.readme_summary.strip()) > 50 else 0.0

    score = min(
        100.0,
        15.0 * keyword_hits
        + 20.0 * required_hits
        + 100.0 * topic_bonus
        + 100.0 * description_bonus
        + 100.0 * readme_bonus,
    )

    if required_hits > 0:
        reason = f"Strong overlap with required skills ({required_hits} matched signals)"
    elif keyword_hits > 0:
        reason = f"Relevant overlap with target job keywords ({keyword_hits} matched signals)"
    else:
        reason = "Selected as one of the closest available technical projects"

    return round(score, 2), reason


def rank_projects(projects: List[GithubProject], parsed_job: Dict[str, Any]) -> List[Dict[str, Any]]:
    ranked = []
    for project in projects:
        score, reason = _score_project(project, parsed_job)
        ranked.append(
            {
                "name": project.name,
                "score": score,
                "reason": reason,
                "description": project.description,
                "readme_summary": project.readme_summary,
                "languages": project.languages,
                "topics": project.topics,
                "html_url": project.html_url,
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:3]