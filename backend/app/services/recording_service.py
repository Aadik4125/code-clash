from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.feature_snapshot import FeatureSnapshot
from app.models.recording import Recording
from app.models.wellness_score import WellnessScore
from app.services.cognitive_scoring_service import compute_rule_based_score
from app.services.feature_extraction_service import extract_features
from app.services.transcription_service import transcribe_audio


def next_session_number(db: Session, user_id: int) -> int:
    last = (
        db.query(Recording)
        .filter(Recording.user_id == user_id)
        .order_by(Recording.session_number.desc())
        .first()
    )
    return 1 if not last else last.session_number + 1


def process_recording(db: Session, recording: Recording, audio_bytes: bytes) -> None:
    transcript = transcribe_audio(audio_bytes)
    features = extract_features(audio_bytes, transcript)
    score_data = compute_rule_based_score(
        features["acoustic"], features["temporal"], features["linguistic"]
    )

    recording.transcript = transcript
    recording.processing_status = "completed"

    snapshot = FeatureSnapshot(
        recording_id=recording.id,
        extractor="librosa",
        acoustic_features=features["acoustic"],
        temporal_features=features["temporal"],
        linguistic_features=features["linguistic"],
    )
    db.add(snapshot)

    db.add(
        WellnessScore(
            recording_id=recording.id,
            score=int(score_data["score"]),
            risk_level=str(score_data["risk_level"]),
            rule_breakdown=dict(score_data["rule_breakdown"]),
        )
    )
    db.commit()

