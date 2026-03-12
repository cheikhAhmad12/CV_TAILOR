from fastapi import FastAPI

from app.core.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.profiles import router as profiles_router
from app.routers.jobs import router as jobs_router
from app.routers.applications import router as applications_router
from app.routers.tailoring import router as tailoring_router

from app.models.user import User
from app.models.profile import Profile
from app.models.job import JobPosting
from app.models.application import ApplicationVersion

app = FastAPI(
    title="AI CV Tailor V3 Backend",
    version="0.2.0",
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(tailoring_router)


@app.get("/")
def root():
    return {"message": "AI CV Tailor V3 backend running"}