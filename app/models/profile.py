from sqlalchemy import Integer, ForeignKey, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), default="Master CV", nullable=False)
    master_cv_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    master_cv_latex: Mapped[str] = mapped_column(Text, default="", nullable=False)
    github_username: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    parsed_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    user = relationship("User", back_populates="profiles")
    applications = relationship("ApplicationVersion", back_populates="profile")
