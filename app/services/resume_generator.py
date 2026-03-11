from typing import Dict, Any, List


def generate_tailored_summary(parsed_cv: Dict[str, Any], parsed_job: Dict[str, Any], selected_projects: List[Dict[str, Any]]) -> str:
    title = parsed_job["title"] or "the target role"
    top_keywords = ", ".join(parsed_job["keywords"][:5]) if parsed_job["keywords"] else "relevant technologies"
    project_names = ", ".join(p["name"] for p in selected_projects[:2]) if selected_projects else "relevant technical projects"

    return (
        f"Candidate targeting {title} with relevant engineering and delivery experience. "
        f"Strong alignment with {top_keywords}. "
        f"Hands-on project work includes {project_names}."
    )


def generate_experience_bullets(parsed_cv: Dict[str, Any], parsed_job: Dict[str, Any]) -> List[str]:
    bullets = []
    kw = ", ".join(parsed_job["keywords"][:4]) if parsed_job["keywords"] else "relevant technologies"

    for exp in parsed_cv["experiences"][:4]:
        prefix = f"{exp['title']} at {exp['company']}" if exp["company"] else exp["title"]
        bullets.append(
            f"{prefix} with experience aligned to {kw}; scope includes {exp['description'][:150].strip()}."
        )

    if not bullets:
        bullets.append(
            f"Professional experience can be positioned toward {parsed_job['title']} by emphasizing ownership, delivery, and technical execution."
        )

    return bullets


def generate_cover_letter(parsed_cv: Dict[str, Any], parsed_job: Dict[str, Any], selected_projects: List[Dict[str, Any]]) -> str:
    projects = ", ".join([p["name"] for p in selected_projects]) if selected_projects else "relevant projects"
    keywords = ", ".join(parsed_job["keywords"][:5]) if parsed_job["keywords"] else "the required stack"

    return f"""Dear Hiring Team,

I am applying for the {parsed_job['title']} position. My background combines practical engineering experience with hands-on technical work aligned with your needs, especially in {keywords}.

In addition to my professional experience, I have worked on projects such as {projects}, which demonstrate my ability to translate technical requirements into concrete deliverables. I am motivated by opportunities where I can contribute quickly while continuing to deepen my expertise.

Thank you for your consideration.

Sincerely,
Candidate
""".strip()


def generate_resume_markdown(
    parsed_cv: Dict[str, Any],
    parsed_job: Dict[str, Any],
    selected_projects: List[Dict[str, Any]],
    tailored_summary: str,
    tailored_experience_bullets: List[str],
) -> str:
    skills = parsed_cv["skills"][:]
    for kw in parsed_job["keywords"]:
        if kw not in skills:
            skills.append(kw)
    skills = skills[:12]

    experience_lines = "\n".join(f"- {b}" for b in tailored_experience_bullets)
    project_lines = "\n".join(
        f"- **{p['name']}** — {p['description'] or p['readme_summary'] or p['reason']}"
        for p in selected_projects
    ) or "- No selected projects"
    education_lines = "\n".join(f"- {e}" for e in parsed_cv["education"]) if parsed_cv["education"] else "- Education available in source CV"

    return f"""# Tailored Resume

## Target Role
{parsed_job['title']}

## Professional Summary
{tailored_summary}

## Core Skills
{", ".join(skills)}

## Professional Experience
{experience_lines}

## Selected Projects
{project_lines}

## Education
{education_lines}
""".strip()