from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.application import ApplicationVersion
from app.models.job import JobPosting
from app.models.profile import Profile
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationResponse

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/", response_model=list[ApplicationResponse])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apps = db.scalars(
        select(ApplicationVersion)
        .where(ApplicationVersion.user_id == current_user.id)
        .order_by(ApplicationVersion.id.desc())
    ).all()
    return list(apps)


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(Profile, payload.profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Profile not found")

    job = db.get(JobPosting, payload.job_posting_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    application = ApplicationVersion(
        user_id=current_user.id,
        profile_id=payload.profile_id,
        job_posting_id=payload.job_posting_id,
        tailored_summary=payload.tailored_summary,
        tailored_resume_markdown=payload.tailored_resume_markdown,
        cover_letter=payload.cover_letter,
        compatibility_score=payload.compatibility_score,
        ats_score=payload.ats_score,
        selected_projects_json=payload.selected_projects_json,
        docx_path=payload.docx_path,
        pdf_path=payload.pdf_path,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app_obj = db.get(ApplicationVersion, application_id)
    if not app_obj or app_obj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return app_obj