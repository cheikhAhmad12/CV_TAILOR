from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourceAgentMessage(Base):
    __tablename__ = "source_agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("source_agent_sessions.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
