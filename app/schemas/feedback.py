"""단원별 진척도(피드백) 스키마."""
from pydantic import BaseModel


class UnitMastery(BaseModel):
    unit: str
    problems_attempted: int
    avg_hints_used: float
    mastery_level: str


class OverallSummary(BaseModel):
    total_attempts: int
    total_hints_used: int
    accuracy_by_difficulty: dict[str, float | None]   # {"쉬움": .., "중간": .., "어려움": ..}
    message: str


class FeedbackResponse(BaseModel):
    summary: OverallSummary
    items: list[UnitMastery]
    weakest_unit: str | None
