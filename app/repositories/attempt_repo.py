"""진척도(attempts) 저장소. 정답을 맞힌(solved) 시도만 기록해 '완료한 문제' 기준으로 집계한다."""
from collections import defaultdict
from app.db.supabase_client import get_client


def record_attempt(user_id: int, problem_id: str, unit: str, hints_used: int, solved: bool) -> None:
    get_client().table("attempts").insert({
        "user_id": user_id,
        "problem_id": problem_id,
        "unit": unit,
        "hints_used": hints_used,
        "solved": solved,
    }).execute()


def _mastery_level(avg_hints: float) -> str:
    if avg_hints < 1.0:
        return "잘함"
    if avg_hints < 2.0:
        return "보통"
    return "취약"


def get_unit_mastery(user_id: int) -> list[dict]:
    """단원별 '푼 문제 수 · 평균 힌트 사용량 · 숙련도'를 그때그때 집계한다."""
    res = (
        get_client()
        .table("attempts")
        .select("unit, hints_used")
        .eq("user_id", user_id)
        .eq("solved", True)
        .execute()
    )

    by_unit: dict[str, list[int]] = defaultdict(list)
    for row in res.data:
        by_unit[row["unit"]].append(row["hints_used"])

    items = []
    for unit, hints in by_unit.items():
        avg_hints = sum(hints) / len(hints)
        items.append({
            "unit": unit,
            "problems_attempted": len(hints),
            "avg_hints_used": round(avg_hints, 1),
            "mastery_level": _mastery_level(avg_hints),
        })
    return sorted(items, key=lambda x: x["avg_hints_used"], reverse=True)
