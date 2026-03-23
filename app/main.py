from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.profiles import router as profiles_router
from app.routers.jobs import router as jobs_router
from app.routers.applications import router as applications_router
from app.routers.tailoring import router as tailoring_router
from app.routers.github import router as github_router
from app.routers.exports import router as exports_router
from app.routers.thesis_discovery import router as thesis_discovery_router

from app.models.user import User
from app.models.profile import Profile
from app.models.job import JobPosting
from app.models.application import ApplicationVersion

app = FastAPI(
    title="AI CV Tailor V3 Backend",
    version="0.3.0",
)

Base.metadata.create_all(bind=engine)
with engine.begin() as conn:
    conn.execute(
        text(
            "ALTER TABLE profiles "
            "ADD COLUMN IF NOT EXISTS master_cv_latex TEXT NOT NULL DEFAULT ''"
        )
    )
    conn.execute(
        text(
            "ALTER TABLE profiles "
            "ADD COLUMN IF NOT EXISTS master_cover_letter_text TEXT NOT NULL DEFAULT ''"
        )
    )
    conn.execute(
        text(
            "ALTER TABLE profiles "
            "ADD COLUMN IF NOT EXISTS master_cover_letter_latex TEXT NOT NULL DEFAULT ''"
        )
    )

ui_dir = Path(__file__).resolve().parent / "ui"
app.mount("/assets", StaticFiles(directory=ui_dir / "assets"), name="assets")

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(tailoring_router)
app.include_router(github_router)
app.include_router(exports_router)
app.include_router(thesis_discovery_router)


@app.get("/")
def root():
    return {"message": "AI CV Tailor V3 backend running"}


@app.get("/ui", include_in_schema=False)
def ui():
    return FileResponse(ui_dir / "index.html")
