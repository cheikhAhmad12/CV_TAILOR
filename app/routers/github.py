from fastapi import APIRouter, HTTPException, status

from app.schemas.github import GithubFetchRequest, GithubFetchResponse
from app.services.github_service import fetch_github_projects, validate_github_username

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/validate")
def github_validate(username: str):
    try:
        return {"valid": validate_github_username(username.strip())}
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub validation failed: {str(e)}",
        )


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
