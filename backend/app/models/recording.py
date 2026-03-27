from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Recording(Base):
    __tablename__ = "recordings"
    __table_args__ = (
        UniqueConstraint("user_id", "session_number", name="uq_recording_user_session"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    recording_date: Mapped[datetime] = mapped_column(
        Date, default=lambda: datetime.now(timezone.utc).date(), index=True, nullable=False
    )
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user = relationship("User", back_populates="recordings")
    features = relationship("FeatureSnapshot", back_populates="recording", cascade="all, delete-orphan")
    scores = relationship("WellnessScore", back_populates="recording", cascade="all, delete-orphan")
    weak_labels = relationship("WeakLabel", back_populates="recording", cascade="all, delete-orphan")

