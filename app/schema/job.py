from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(default="", max_length=255)
    source_url: str = ""
    raw_text: str = Field(min_length=1)


class JobUpdate(BaseModel):
    title: str | None = None
    source_url: str | None = None
    raw_text: str | None = None


class JobResponse(BaseModel):
    id: int
    title: str
    source_url: str
    raw_text: str
    parsed_json: str

    class Config:
        from_attributes = True