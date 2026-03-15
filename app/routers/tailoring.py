from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.tailoring import TailoringRunRequest, TailoringRunResponse
from app.services.tailoring_engine import run_tailoring_engine


router = APIRouter(prefix="/tailoring", tags=["tailoring"])


@router.post("/run", response_model=TailoringRunResponse)
def run_tailoring(
    payload: TailoringRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = run_tailoring_engine(
            db=db,
            current_user_id=current_user.id,
            profile_id=payload.profile_id,
            job_posting_id=payload.job_posting_id,
            github_projects=payload.github_projects,
            master_cv_latex=payload.master_cv_latex,
            output_language=payload.output_language,
            use_llm=payload.use_llm,
        )
        return TailoringRunResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tailoring failed: {str(e)}",
        )
