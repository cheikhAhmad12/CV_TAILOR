import base64
import requests
from typing import List

from app.schemas.github import GithubProject


GITHUB_API = "https://api.github.com"


def _get_readme_summary(full_name: str) -> str:
    url = f"{GITHUB_API}/repos/{full_name}/readme"
    resp = requests.get(
        url,
        timeout=20,
        headers={"Accept": "application/vnd.github+json"},
    )
    if resp.status_code != 200:
        return ""

    data = resp.json()
    content = data.get("content", "")
    if not content:
        return ""

    try:
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return ""

    return decoded[:1500].strip()


def fetch_github_projects(username: str, max_repos: int = 8) -> List[GithubProject]:
    url = f"{GITHUB_API}/users/{username}/repos"
    params = {"sort": "updated", "per_page": max_repos}
    resp = requests.get(
        url,
        params=params,
        timeout=20,
        headers={"Accept": "application/vnd.github+json"},
    )
    resp.raise_for_status()

    repos = resp.json()
    projects: List[GithubProject] = []

    for repo in repos:
        if repo.get("fork"):
            continue

        full_name = repo["full_name"]
        readme_summary = _get_readme_summary(full_name)
        languages = [repo["language"]] if repo.get("language") else []
        topics = repo.get("topics", []) or []

        projects.append(
            GithubProject(
                name=repo["name"],
                description=repo.get("description") or "",
                readme_summary=readme_summary,
                languages=languages,
                topics=topics,
                html_url=repo.get("html_url", ""),
            )
        )

    return projects[:max_repos]