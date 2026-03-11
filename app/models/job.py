from sqlalchemy import Integer, ForeignKey, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    user = relationship("User", back_populates="jobs")
    applications = relationship("ApplicationVersion", back_populates="job_posting")