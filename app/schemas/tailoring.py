from pydantic import BaseModel, Field
from typing import List, Literal

from app.schemas.github import GithubProject


class TailoringRunRequest(BaseModel):
    profile_id: int
    job_posting_id: int
    github_projects: List[GithubProject] = Field(default_factory=list)
    master_cv_latex: str = ""
    output_language: Literal["fr", "en"] = "fr"
    use_llm: bool = False


class RankedProject(BaseModel):
    name: str
    score: float
    reason: str
    description: str
    readme_summary: str
    languages: List[str]
    topics: List[str]
    html_url: str = ""


class TailoringRunResponse(BaseModel):
    application_id: int
    tailored_summary: str
    tailored_resume_markdown: str
    cover_letter: str
    compatibility_score: float
    ats_score: float
    selected_projects: List[RankedProject]
    parsed_job_json: str
    parsed_profile_json: str
    docx_path: str = ""
    pdf_path: str = ""
