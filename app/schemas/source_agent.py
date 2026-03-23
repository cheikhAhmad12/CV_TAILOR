from pydantic import BaseModel, Field


class ThesisSourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_url: str = ""


class ThesisSourceResponse(BaseModel):
    id: int
    name: str
    base_url: str
    status: str
    strategy: str
    requires_auth: bool
    config_json: str

    class Config:
        from_attributes = True


class SourceAgentSessionCreateRequest(BaseModel):
    source_id: int


class SourceAgentMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class SourceAgentMessageResponse(BaseModel):
    id: int
    role: str
    content: str

    class Config:
        from_attributes = True


class SourceAgentSessionResponse(BaseModel):
    id: int
    source_id: int
    status: str
    draft_config_json: str
    messages: list[SourceAgentMessageResponse]
