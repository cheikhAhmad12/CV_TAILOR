from sqlalchemy import Integer, ForeignKey, Text, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationVersion(Base):
    __tablename__ = "application_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    job_posting_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), index=True, nullable=False)

    tailored_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tailored_resume_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cover_letter: Mapped[str] = mapped_column(Text, default="", nullable=False)

    compatibility_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ats_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    selected_projects_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    docx_path: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(1000), default="", nullable=False)

    user = relationship("User", back_populates="applications")
    profile = relationship("Profile", back_populates="applications")
    job_posting = relationship("JobPosting", back_populates="applications")