from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    profile_id: int
    job_posting_id: int
    tailored_summary: str = ""
    tailored_resume_markdown: str = ""
    cover_letter: str = ""
    compatibility_score: float = 0.0
    ats_score: float = 0.0
    selected_projects_json: str = "[]"
    docx_path: str = ""
    pdf_path: str = ""


class ApplicationResponse(BaseModel):
    id: int
    profile_id: int
    job_posting_id: int
    tailored_summary: str
    tailored_resume_markdown: str
    cover_letter: str
    compatibility_score: float
    ats_score: float
    selected_projects_json: str
    docx_path: str
    pdf_path: str

    class Config:
        from_attributes = True