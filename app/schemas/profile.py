from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    title: str = Field(default="Master CV", min_length=1, max_length=255)
    master_cv_text: str = Field(min_length=1)
    master_cv_latex: str = ""
    master_cover_letter_text: str = ""
    master_cover_letter_latex: str = ""
    github_username: str = ""


class ProfileUpdate(BaseModel):
    title: str | None = None
    master_cv_text: str | None = None
    master_cv_latex: str | None = None
    master_cover_letter_text: str | None = None
    master_cover_letter_latex: str | None = None
    github_username: str | None = None


class ProfileResponse(BaseModel):
    id: int
    title: str
    master_cv_text: str
    master_cv_latex: str
    master_cover_letter_text: str
    master_cover_letter_latex: str
    github_username: str
    parsed_summary_json: str

    class Config:
        from_attributes = True
