from pydantic import BaseModel, Field
from typing import List


class GithubProject(BaseModel):
    name: str
    description: str = ""
    readme_summary: str = ""
    languages: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    html_url: str = ""


class GithubFetchRequest(BaseModel):
    username: str
    max_repos: int = 8


class GithubFetchResponse(BaseModel):
    projects: List[GithubProject]