"""단원별 진척도(피드백) 스키마."""
from pydantic import BaseModel


class UnitMastery(BaseModel):
    unit: str
    problems_attempted: int
    avg_hints_used: float
    mastery_level: str


class FeedbackResponse(BaseModel):
    items: list[UnitMastery]
    weakest_unit: str | None
