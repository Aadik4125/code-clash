from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recordings.id"), index=True, nullable=False)
    extractor: Mapped[str] = mapped_column(String(40), nullable=False, default="librosa")
    acoustic_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    temporal_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    linguistic_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    recording = relationship("Recording", back_populates="features")

