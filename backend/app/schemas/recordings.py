from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    recording_id: int
    session_number: int
    processing_status: str
    storage_uri: str


class WeakLabelRequest(BaseModel):
    stress_score: int | None = Field(default=None, ge=0, le=10)
    survey_payload: dict = Field(default_factory=dict)
    cognitive_test_payload: dict = Field(default_factory=dict)

