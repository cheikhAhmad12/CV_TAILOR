import json
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.job import JobPosting
from app.models.application import ApplicationVersion
from app.schemas.github import GithubProject
from app.services.cv_parser import parse_cv
from app.services.job_parser import parse_job_description
from app.services.project_selector import rank_projects
from app.services.resume_generator import (
    generate_tailored_summary,
    generate_experience_bullets,
    generate_cover_letter,
    generate_resume_markdown,
)
from app.services.scoring import compute_compatibility_score, compute_ats_score
from app.services.github_service import fetch_github_projects
from app.services.docx_exporter import export_resume_to_docx
from app.services.latex_exporter import export_latex_to_pdf_with_tectonic


def run_tailoring_engine(
    db: Session,
    current_user_id: int,
    profile_id: int,
    job_posting_id: int,
    github_projects: list[GithubProject],
    master_cv_latex: str = "",
    output_language: str = "fr",
) -> dict:
    profile = db.get(Profile, profile_id)
    if not profile or profile.user_id != current_user_id:
        raise ValueError("Profile not found")

    job = db.get(JobPosting, job_posting_id)
    if not job or job.user_id != current_user_id:
        raise ValueError("Job not found")

    parsed_cv = parse_cv(profile.master_cv_text)
    parsed_job = parse_job_description(job.raw_text)

    projects_to_use = github_projects
    if not projects_to_use and profile.github_username.strip():
        try:
            projects_to_use = fetch_github_projects(profile.github_username.strip(), max_repos=8)
        except Exception:
            projects_to_use = []

    selected_projects = rank_projects(projects_to_use, parsed_job)

    tailored_summary = generate_tailored_summary(
        parsed_cv, parsed_job, selected_projects, output_language=output_language
    )
    tailored_experience_bullets = generate_experience_bullets(
        parsed_cv, parsed_job, output_language=output_language
    )
    cover_letter = generate_cover_letter(
        parsed_cv, parsed_job, selected_projects, output_language=output_language
    )
    tailored_resume_markdown = generate_resume_markdown(
        parsed_cv=parsed_cv,
        parsed_job=parsed_job,
        selected_projects=selected_projects,
        tailored_summary=tailored_summary,
        tailored_experience_bullets=tailored_experience_bullets,
        output_language=output_language,
    )

    compatibility_score = compute_compatibility_score(parsed_cv, parsed_job, selected_projects)
    ats_score = compute_ats_score(tailored_resume_markdown, parsed_job)
    docx_path = export_resume_to_docx(tailored_resume_markdown)
    latex_source = (master_cv_latex or "").strip() or (profile.master_cv_latex or "").strip()

    pdf_path = export_latex_to_pdf_with_tectonic(
        master_cv_latex=latex_source,
        tailored_summary=tailored_summary,
        tailored_experience_bullets=tailored_experience_bullets,
        selected_projects=selected_projects,
        output_language=output_language,
    )

    profile.parsed_summary_json = json.dumps(parsed_cv, ensure_ascii=False)
    job.parsed_json = json.dumps(parsed_job, ensure_ascii=False)

    application = ApplicationVersion(
        user_id=current_user_id,
        profile_id=profile.id,
        job_posting_id=job.id,
        tailored_summary=tailored_summary,
        tailored_resume_markdown=tailored_resume_markdown,
        cover_letter=cover_letter,
        compatibility_score=compatibility_score,
        ats_score=ats_score,
        selected_projects_json=json.dumps(selected_projects, ensure_ascii=False),
        docx_path=docx_path,
        pdf_path=pdf_path,
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "application_id": application.id,
        "tailored_summary": tailored_summary,
        "tailored_resume_markdown": tailored_resume_markdown,
        "cover_letter": cover_letter,
        "compatibility_score": compatibility_score,
        "ats_score": ats_score,
        "selected_projects": selected_projects,
        "parsed_job_json": json.dumps(parsed_job, ensure_ascii=False),
        "parsed_profile_json": json.dumps(parsed_cv, ensure_ascii=False),
        "docx_path": docx_path,
        "pdf_path": pdf_path,
    }
