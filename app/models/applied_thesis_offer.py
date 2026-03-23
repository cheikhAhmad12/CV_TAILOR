from sqlalchemy import Integer, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppliedThesisOffer(Base):
    __tablename__ = "applied_thesis_offers"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "source_offer_id", name="uq_applied_thesis_offer_user_source_offer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    source: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_offer_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    detail_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
