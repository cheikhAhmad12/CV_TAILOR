from fastapi import APIRouter, HTTPException, status

from app.schemas.github import GithubFetchRequest, GithubFetchResponse
from app.services.github_service import fetch_github_projects

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/fetch", response_model=GithubFetchResponse)
def github_fetch(payload: GithubFetchRequest):
    try:
        projects = fetch_github_projects(payload.username, payload.max_repos)
        return GithubFetchResponse(projects=projects)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub fetch failed: {str(e)}",
        )