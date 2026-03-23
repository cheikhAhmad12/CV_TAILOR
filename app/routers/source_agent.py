from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.source_agent_message import SourceAgentMessage
from app.models.source_agent_session import SourceAgentSession
from app.models.thesis_source import ThesisSource
from app.models.user import User
from app.schemas.source_agent import (
    SourceAgentMessageCreateRequest,
    SourceAgentMessageResponse,
    SourceAgentSessionCreateRequest,
    SourceAgentSessionResponse,
    ThesisSourceCreateRequest,
    ThesisSourceResponse,
)
from app.services.source_agent import (
    assistant_welcome_message,
    handle_source_agent_message,
    persist_message,
)


router = APIRouter(prefix="/source-agent", tags=["source-agent"])
sources_router = APIRouter(prefix="/thesis-sources", tags=["thesis-sources"])


def _session_response(db: Session, session: SourceAgentSession) -> SourceAgentSessionResponse:
    messages = db.scalars(
        select(SourceAgentMessage)
        .where(SourceAgentMessage.session_id == session.id)
        .order_by(SourceAgentMessage.id.asc())
    ).all()
    return SourceAgentSessionResponse(
        id=session.id,
        source_id=session.source_id,
        status=session.status,
        draft_config_json=session.draft_config_json,
        messages=[
            SourceAgentMessageResponse(id=msg.id, role=msg.role, content=msg.content)
            for msg in messages
        ],
    )


@sources_router.get("/", response_model=list[ThesisSourceResponse])
def list_thesis_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.scalars(
        select(ThesisSource)
        .where(ThesisSource.user_id == current_user.id)
        .order_by(ThesisSource.id.desc())
    ).all()
    return list(items)


@sources_router.post("/", response_model=ThesisSourceResponse, status_code=status.HTTP_201_CREATED)
def create_thesis_source(
    payload: ThesisSourceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = ThesisSource(
        user_id=current_user.id,
        name=payload.name,
        base_url=payload.base_url,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.post("/sessions", response_model=SourceAgentSessionResponse, status_code=status.HTTP_201_CREATED)
def create_source_agent_session(
    payload: SourceAgentSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = db.get(ThesisSource, payload.source_id)
    if not source or source.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Source not found")

    session = SourceAgentSession(
        user_id=current_user.id,
        source_id=source.id,
        status="open",
        draft_config_json=source.config_json,
    )
    db.add(session)
    db.flush()
    persist_message(db, session.id, "assistant", assistant_welcome_message(source.name))
    db.commit()
    db.refresh(session)
    return _session_response(db, session)


@router.get("/sessions/{session_id}", response_model=SourceAgentSessionResponse)
def get_source_agent_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(SourceAgentSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_response(db, session)


@router.post("/sessions/{session_id}/messages", response_model=SourceAgentSessionResponse)
def send_source_agent_message(
    session_id: int,
    payload: SourceAgentMessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(SourceAgentSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    source = db.get(ThesisSource, session.source_id)
    if not source or source.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Source not found")

    persist_message(db, session.id, "user", payload.content)
    _, assistant_text = handle_source_agent_message(db, source, session, payload.content)
    persist_message(db, session.id, "assistant", assistant_text)
    db.commit()
    db.refresh(session)
    return _session_response(db, session)
