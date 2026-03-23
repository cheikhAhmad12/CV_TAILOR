from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourceAgentSession(Base):
    __tablename__ = "source_agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("thesis_sources.id"), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(64), nullable=False, default="open")
    draft_config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
