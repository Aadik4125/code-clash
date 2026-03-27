from __future__ import annotations

import io
from typing import Any

from app.celery_app import celery_app
from app.core.settings import get_settings
from app.db.session import SessionLocal

from app.services.storage_service import StorageService
from app.services.transcription_service import transcribe_audio
from app.services.feature_extraction_service import extract_features
from app.services.cognitive_scoring_service import compute_rule_based_score

from app.models.recording import Recording
from app.models.feature_snapshot import FeatureSnapshot
from app.models.wellness_score import WellnessScore


@celery_app.task(name='tasks.process_recording')
def process_recording(recording_id: int) -> dict[str, Any]:
    settings = get_settings()
    storage = StorageService()

    db = SessionLocal()
    try:
        rec: Recording | None = db.query(Recording).filter(Recording.id == recording_id).first()
        if not rec:
            return {"error": "recording_not_found"}

        # Load audio bytes
        uri = rec.storage_uri
        audio_bytes = b""
        if uri.startswith("s3://"):
            # Let StorageService handle S3
            # storage.save_audio handles uploads; implement download via boto3 directly here
            s3 = storage._get_s3_client()
            # parse s3://bucket/key
            _, path = uri.split("s3://", 1)
            bucket, key = path.split('/', 1)
            resp = s3.get_object(Bucket=bucket, Key=key)
            audio_bytes = resp['Body'].read()
        else:
            # local file path
            try:
                with open(uri, 'rb') as fh:
                    audio_bytes = fh.read()
            except Exception:
                audio_bytes = b""

        # Transcribe (best-effort)
        transcript = transcribe_audio(audio_bytes)

        # Extract features
        features = extract_features(audio_bytes, transcript)

        # Persist FeatureSnapshot
        fs = FeatureSnapshot(
            recording_id=rec.id,
            extractor='librosa_celery',
            acoustic_features=features.get('acoustic', {}),
            temporal_features=features.get('temporal', {}),
            linguistic_features=features.get('linguistic', {}),
        )
        db.add(fs)
        db.commit()
        db.refresh(fs)

        # Compute rule-based wellness score
        score_payload = compute_rule_based_score(
            fs.acoustic_features, fs.temporal_features, fs.linguistic_features
        )

        ws = WellnessScore(
            recording_id=rec.id,
            score=int(score_payload.get('score', 0)),
            risk_level=str(score_payload.get('risk_level', 'unknown')),
            rule_breakdown=score_payload.get('rule_breakdown', {}),
        )
        db.add(ws)
        db.commit()
        db.refresh(ws)

        # Update recording with transcript and processed status
        rec.transcript = transcript
        rec.processing_status = 'processed'
        db.add(rec)
        db.commit()

        return {"status": "ok", "recording_id": rec.id, "feature_snapshot_id": fs.id, "wellness_score_id": ws.id}
    finally:
        db.close()
