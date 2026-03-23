import re
from typing import Any

import requests


API_BASE = "https://app.doctorat.gouv.fr/api"
SEARCH_ENDPOINT = f"{API_BASE}/propositions-these"
DETAIL_ENDPOINT = f"{SEARCH_ENDPOINT}/proposition"
SOURCE_NAME = "doctorat_gouv"
USER_AGENT = "CV-Tailor/0.3 (+https://app.doctorat.gouv.fr)"


def fetch_thesis_offers(
    page: int,
    size: int,
    discipline: str = "",
    localisation: str = "",
) -> dict[str, Any]:
    params = {"page": page, "size": size}
    if discipline:
        params["discipline"] = discipline
    if localisation:
        params["localisation"] = localisation

    response = requests.get(
        SEARCH_ENDPOINT,
        params=params,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=25,
    )
    response.raise_for_status()
    return response.json()


def fetch_thesis_offer_detail(source_id: str) -> dict[str, Any]:
    response = requests.get(
        DETAIL_ENDPOINT,
        params={"id": source_id},
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=25,
    )
    response.raise_for_status()
    return response.json()


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def build_profile_search_intent(parsed_cv: dict[str, Any]) -> dict[str, Any]:
    keywords: list[str] = []

    for skill in parsed_cv.get("skills", [])[:20]:
        if isinstance(skill, str) and skill.strip():
            keywords.append(skill.strip())

    summary = str(parsed_cv.get("summary", "")).strip()
    keywords.extend(re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-\+]{2,}", summary))

    for experience in parsed_cv.get("experiences", [])[:4]:
        keywords.extend(
            re.findall(
                r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-\+]{2,}",
                str(experience.get("description", "")).strip(),
            )
        )

    deduped: list[str] = []
    seen = set()
    for keyword in keywords:
        normalized = _normalize_token(keyword)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(keyword)

    return {
        "keywords": deduped[:25],
        "summary": summary[:500],
    }


def score_thesis_offer(offer: dict[str, Any], intent: dict[str, Any]) -> tuple[float, str]:
    keywords = intent.get("keywords", [])
    haystack = " ".join(
        [
            str(offer.get("theseTitre", "")),
            str(offer.get("specialite", "")),
            str(offer.get("thematiqueRecherche", "")),
            str(offer.get("resume", "")),
            str(offer.get("profilRecherche", "")),
            str(offer.get("uniteRechercheLibelle", "")),
            " ".join(str(v) for v in (offer.get("motsCles") or {}).values()),
            " ".join(str(v) for v in (offer.get("motsClesAnglais") or {}).values()),
        ]
    ).lower()

    hits: list[str] = []
    score = 0.0
    for keyword in keywords:
        key = keyword.strip().lower()
        if not key:
            continue
        if key in haystack:
            hits.append(keyword)
            score += 8.0 if len(key) > 4 else 4.0

    if any(term in haystack for term in ["phd", "doctorat", "thèse", "these", "cifre"]):
        score += 10.0

    score = min(score, 100.0)
    if hits:
        return round(score, 2), f"Matched profile keywords: {', '.join(hits[:5])}"

    return round(score, 2), "Weak direct overlap; retained as potentially relevant doctoral offer"


def normalize_thesis_offer(offer: dict[str, Any], score: float, reason: str) -> dict[str, Any]:
    source_id = str(
        offer.get("id")
        or offer.get("propositionId")
        or offer.get("theseId")
        or offer.get("theseTitre")
    ).strip()
    detail_url = f"https://app.doctorat.gouv.fr/proposition?id={source_id}" if source_id else ""
    return {
        "source": SOURCE_NAME,
        "source_id": source_id,
        "title": str(offer.get("theseTitre", "")).strip(),
        "lab_name": str(offer.get("uniteRechercheLibelle", "")).strip(),
        "city": str(offer.get("uniteRechercheVille", "")).strip(),
        "speciality": str(offer.get("specialite", "")).strip(),
        "research_theme": str(offer.get("thematiqueRecherche", "")).strip(),
        "summary": str(offer.get("resume", "")).strip(),
        "candidate_profile": str(offer.get("profilRecherche", "")).strip(),
        "application_url": str(offer.get("urlCandidature", "")).strip(),
        "detail_url": detail_url,
        "funding_type": str(offer.get("typeFinancement", "")).strip(),
        "contact_name": str(offer.get("contactNom", "")).strip(),
        "match_score": score,
        "match_reason": reason,
        "raw_payload": offer,
    }


def thesis_offer_to_raw_text(offer: dict[str, Any]) -> str:
    parts = [
        f"Title: {offer.get('title', '')}",
        f"Lab: {offer.get('lab_name', '')}",
        f"City: {offer.get('city', '')}",
        f"Speciality: {offer.get('speciality', '')}",
        f"Research Theme: {offer.get('research_theme', '')}",
        f"Funding Type: {offer.get('funding_type', '')}",
        f"Candidate Profile: {offer.get('candidate_profile', '')}",
        f"Summary: {offer.get('summary', '')}",
        f"Application URL: {offer.get('application_url', '')}",
        f"Detail URL: {offer.get('detail_url', '')}",
        f"Match Reason: {offer.get('match_reason', '')}",
    ]
    return "\n\n".join(part for part in parts if part and not part.endswith(": "))
