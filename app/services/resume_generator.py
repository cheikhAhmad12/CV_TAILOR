from typing import Dict, Any, List


def generate_tailored_summary(
    parsed_cv: Dict[str, Any],
    parsed_job: Dict[str, Any],
    selected_projects: List[Dict[str, Any]],
    output_language: str = "fr",
) -> str:
    lang = "en" if output_language == "en" else "fr"
    title = parsed_job["title"] or ("the target role" if lang == "en" else "le poste cible")
    top_keywords = ", ".join(parsed_job["keywords"][:5]) if parsed_job["keywords"] else (
        "relevant technologies" if lang == "en" else "des technologies pertinentes"
    )
    project_names = ", ".join(p["name"] for p in selected_projects[:2]) if selected_projects else (
        "relevant technical projects" if lang == "en" else "des projets techniques pertinents"
    )

    if lang == "en":
        return (
            f"Candidate targeting {title} with solid engineering and delivery experience. "
            f"Strong alignment with {top_keywords}. "
            f"Technical achievements notably include {project_names}."
        )

    return (
        f"Candidat cible le poste {title} avec une experience solide en ingenierie et en delivery. "
        f"Forte adequation avec {top_keywords}. "
        f"Les realisations techniques incluent notamment {project_names}."
    )


def generate_experience_bullets(
    parsed_cv: Dict[str, Any],
    parsed_job: Dict[str, Any],
    output_language: str = "fr",
) -> List[str]:
    lang = "en" if output_language == "en" else "fr"
    bullets = []
    kw = ", ".join(parsed_job["keywords"][:4]) if parsed_job["keywords"] else (
        "relevant technologies" if lang == "en" else "des technologies pertinentes"
    )

    for exp in parsed_cv["experiences"][:4]:
        if lang == "en":
            prefix = f"{exp['title']} at {exp['company']}" if exp["company"] else exp["title"]
            bullets.append(
                f"{prefix}, experience aligned with {kw}; scope: {exp['description'][:150].strip()}."
            )
        else:
            prefix = f"{exp['title']} chez {exp['company']}" if exp["company"] else exp["title"]
            bullets.append(
                f"{prefix}, experience alignee avec {kw}; perimetre: {exp['description'][:150].strip()}."
            )

    if not bullets:
        if lang == "en":
            bullets.append(
                f"Professional experience can be positioned toward {parsed_job['title']} by emphasizing ownership, delivery, and technical execution."
            )
        else:
            bullets.append(
                f"L'experience professionnelle peut etre positionnee vers {parsed_job['title']} en mettant en avant ownership, delivery et execution technique."
            )

    return bullets


def generate_cover_letter(
    parsed_cv: Dict[str, Any],
    parsed_job: Dict[str, Any],
    selected_projects: List[Dict[str, Any]],
    output_language: str = "fr",
) -> str:
    lang = "en" if output_language == "en" else "fr"
    projects = ", ".join([p["name"] for p in selected_projects]) if selected_projects else (
        "relevant projects" if lang == "en" else "des projets pertinents"
    )
    keywords = ", ".join(parsed_job["keywords"][:5]) if parsed_job["keywords"] else (
        "the required stack" if lang == "en" else "la stack demandee"
    )

    if lang == "en":
        return f"""Dear Hiring Team,

I am applying for the {parsed_job['title']} position. My background combines practical engineering experience with technical achievements aligned with your needs, especially around {keywords}.

In addition to my professional experience, I have worked on projects such as {projects}, which demonstrate my ability to turn technical requirements into concrete deliverables. I am motivated by environments where I can contribute quickly while deepening my expertise.

Thank you for your consideration.

Sincerely,
Candidate
""".strip()

    return f"""Madame, Monsieur,

Je candidate au poste {parsed_job['title']}. Mon parcours combine une experience d'ingenierie pratique avec des realisations techniques alignees avec vos besoins, notamment autour de {keywords}.

En complement de mon experience professionnelle, j'ai travaille sur des projets tels que {projects}, qui montrent ma capacite a transformer des exigences techniques en livrables concrets. Je suis motive par les environnements ou je peux contribuer rapidement tout en approfondissant mon expertise.

Je vous remercie pour votre consideration.

Cordialement,
Candidat
""".strip()


def generate_resume_markdown(
    parsed_cv: Dict[str, Any],
    parsed_job: Dict[str, Any],
    selected_projects: List[Dict[str, Any]],
    tailored_summary: str,
    tailored_experience_bullets: List[str],
    output_language: str = "fr",
) -> str:
    lang = "en" if output_language == "en" else "fr"
    skills = parsed_cv["skills"][:]
    for kw in parsed_job["keywords"]:
        if kw not in skills:
            skills.append(kw)
    skills = skills[:12]

    summary_text = (parsed_cv.get("summary") or "").strip() or tailored_summary
    experience_lines_list = []
    for exp in parsed_cv.get("experiences", []):
        title = str(exp.get("title", "")).strip()
        company = str(exp.get("company", "")).strip()
        description = str(exp.get("description", "")).strip()
        header = f"{title} at {company}" if company else title
        line = f"{header} — {description}".strip(" —")
        if line:
            experience_lines_list.append(line)
    if not experience_lines_list:
        experience_lines_list = tailored_experience_bullets[:]

    experience_lines = "\n".join(f"- {b}" for b in experience_lines_list)
    project_lines = "\n".join(
        f"- **{p['name']}** — {p['description'] or p['readme_summary'] or p['reason']}"
        for p in selected_projects
    ) or ("- No selected projects" if lang == "en" else "- Aucun projet selectionne")
    education_lines = "\n".join(f"- {e}" for e in parsed_cv["education"]) if parsed_cv["education"] else (
        "- Education available in source CV" if lang == "en" else "- Formation disponible dans le CV source"
    )

    if lang == "en":
        return f"""# Tailored Resume

## Target Role
{parsed_job['title']}

## Professional Summary
{summary_text}

## Core Skills
{", ".join(skills)}

## Professional Experience
{experience_lines}

## Selected Projects
{project_lines}

## Education
{education_lines}
""".strip()

    return f"""# CV cible

## Poste cible
{parsed_job['title']}

## Resume professionnel
{summary_text}

## Competences cles
{", ".join(skills)}

## Experience professionnelle
{experience_lines}

## Projets selectionnes
{project_lines}

## Formation
{education_lines}
""".strip()
