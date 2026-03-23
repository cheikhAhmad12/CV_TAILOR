from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.applied_thesis_offer import AppliedThesisOffer
from app.models.job import JobPosting
from app.models.profile import Profile
from app.models.user import User
from app.schemas.thesis_discovery import (
    AppliedThesisOfferCreateRequest,
    AppliedThesisOfferResponse,
    ThesisDiscoveryImportRequest,
    ThesisDiscoveryImportResponse,
    ThesisDiscoverySearchRequest,
    ThesisDiscoverySearchResponse,
    ThesisOffer,
)
from app.services.cv_parser import parse_cv
from app.services.anrt_cifre_service import ANRT_CIFRE_SOURCE, fetch_anrt_cifre_offers
from app.services.doctorat_gouv_service import (
    SOURCE_NAME as DOCTORAT_GOUV_SOURCE,
    build_profile_search_intent,
    fetch_thesis_offers,
    normalize_thesis_offer,
    score_thesis_offers,
)


router = APIRouter(prefix="/thesis-discovery", tags=["thesis-discovery"])


@router.post("/search", response_model=ThesisDiscoverySearchResponse)
def search_thesis_offers(
    payload: ThesisDiscoverySearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, payload.profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Profile not found")

    parsed_cv = parse_cv(profile.master_cv_text)
    intent = build_profile_search_intent(parsed_cv)

    collected: list[dict] = []
    try:
        if payload.source == DOCTORAT_GOUV_SOURCE:
            for page in range(payload.page_limit):
                data = fetch_thesis_offers(
                    page=page,
                    size=payload.page_size,
                    discipline=payload.discipline,
                    localisation=payload.localisation,
                )
                collected.extend(data.get("content", []) or [])
        elif payload.source == ANRT_CIFRE_SOURCE:
            collected = fetch_anrt_cifre_offers(
                page_limit=payload.page_limit,
                page_size=payload.page_size,
                discipline=payload.discipline,
                localisation=payload.localisation,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported thesis source: {payload.source}")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Thesis discovery failed: {str(exc)}",
        ) from exc

    applied_offer_keys = {
        (row.source, row.source_offer_id)
        for row in db.scalars(
            select(AppliedThesisOffer).where(AppliedThesisOffer.user_id == current_user.id)
        ).all()
    }

    ranked: list[dict] = []
    for offer, score, reason in score_thesis_offers(collected, intent):
        normalized = normalize_thesis_offer(offer, score, reason)
        offer_key = (normalized.get("source", ""), normalized.get("source_id", ""))
        if offer_key in applied_offer_keys:
            continue
        ranked.append(normalized)

    ranked.sort(key=lambda item: item["match_score"], reverse=True)
    return ThesisDiscoverySearchResponse(
        total_candidates=len(collected),
        offers=[ThesisOffer(**item) for item in ranked[: payload.page_size]],
    )


@router.post("/import", response_model=ThesisDiscoveryImportResponse, status_code=status.HTTP_201_CREATED)
def import_thesis_offer(
    payload: ThesisDiscoveryImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = JobPosting(
        user_id=current_user.id,
        title=payload.title,
        source_url=payload.source_url,
        raw_text=payload.raw_text,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return ThesisDiscoveryImportResponse(
        job_id=job.id,
        title=job.title,
        source_url=job.source_url,
        raw_text=job.raw_text,
    )


@router.post("/applied", response_model=AppliedThesisOfferResponse, status_code=status.HTTP_201_CREATED)
def mark_thesis_offer_as_applied(
    payload: AppliedThesisOfferCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.scalar(
        select(AppliedThesisOffer).where(
            AppliedThesisOffer.user_id == current_user.id,
            AppliedThesisOffer.source == payload.source,
            AppliedThesisOffer.source_offer_id == payload.source_id,
        )
    )
    if existing:
        return existing

    applied = AppliedThesisOffer(
        user_id=current_user.id,
        source=payload.source,
        source_offer_id=payload.source_id,
        title=payload.title,
        detail_url=payload.detail_url,
    )
    db.add(applied)
    db.commit()
    db.refresh(applied)
    return applied
