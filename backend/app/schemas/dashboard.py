from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: str
    score: int


class DashboardResponse(BaseModel):
    user_id: int
    total_recordings: int
    latest_score: int | None
    trends: list[TrendPoint]

