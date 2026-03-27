from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WeakLabel(Base):
    __tablename__ = "weak_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recordings.id"), index=True, nullable=False)
    stress_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    survey_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cognitive_test_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), default="self_report", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    recording = relationship("Recording", back_populates="weak_labels")

