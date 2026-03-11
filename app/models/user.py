from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    profiles = relationship("Profile", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("JobPosting", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationVersion", back_populates="user", cascade="all, delete-orphan")