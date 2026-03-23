from pydantic import BaseModel, Field


class ThesisDiscoverySearchRequest(BaseModel):
    profile_id: int
    page_limit: int = Field(default=3, ge=1, le=10)
    page_size: int = Field(default=20, ge=1, le=50)
    discipline: str = ""
    localisation: str = ""


class ThesisOffer(BaseModel):
    source: str = "doctorat_gouv"
    source_id: str
    title: str
    lab_name: str = ""
    city: str = ""
    speciality: str = ""
    research_theme: str = ""
    summary: str = ""
    candidate_profile: str = ""
    application_url: str = ""
    detail_url: str = ""
    funding_type: str = ""
    contact_name: str = ""
    match_score: float = 0.0
    match_reason: str = ""
    raw_payload: dict = Field(default_factory=dict)


class ThesisDiscoverySearchResponse(BaseModel):
    total_candidates: int
    offers: list[ThesisOffer]


class ThesisDiscoveryImportRequest(BaseModel):
    title: str
    source_url: str = ""
    raw_text: str = Field(min_length=1)


class ThesisDiscoveryImportResponse(BaseModel):
    job_id: int
    title: str
    source_url: str
    raw_text: str
