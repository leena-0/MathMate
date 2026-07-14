"""진척도(attempts) 저장소.

단원별 숙련도(get_unit_mastery)는 정답을 맞힌(solved) 시도만 기록해 '완료한 문제' 기준으로 집계한다.
난이도별 정답률(get_overall_summary)은 힌트 3단계를 다 쓰고 포기(공개)한 시도까지 포함한
'전체 시도' 기준으로 집계한다 — 그래야 정답률이라는 지표가 의미를 가진다.
"""
from collections import defaultdict
from app.db.supabase_client import get_client

_DIFFICULTIES = ("쉬움", "중간", "어려움")


def record_attempt(user_id: int, problem_id: str, unit: str, hints_used: int, solved: bool,
                    grade: int | None = None, semester: int | None = None,
                    difficulty: str | None = None) -> None:
    get_client().table("attempts").insert({
        "user_id": user_id,
        "problem_id": problem_id,
        "unit": unit,
        "hints_used": hints_used,
        "solved": solved,
        "grade": grade,
        "semester": semester,
        "difficulty": difficulty,
    }).execute()


def _mastery_level(avg_hints: float) -> str:
    if avg_hints < 1.0:
        return "잘함"
    if avg_hints < 2.0:
        return "보통"
    return "취약"


def get_unit_mastery(user_id: int, grade: int | None = None, semester: int | None = None) -> list[dict]:
    """단원별 '푼 문제 수 · 평균 힌트 사용량 · 숙련도'를 그때그때 집계한다.
    grade/semester를 넘기면 그 학년·학기에 푼 문제만으로 좁혀서 집계한다."""
    query = get_client().table("attempts").select("unit, hints_used").eq("user_id", user_id).eq("solved", True)
    if grade is not None:
        query = query.eq("grade", grade)
    if semester is not None:
        query = query.eq("semester", semester)
    res = query.execute()

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
            "_avg_hints_raw": avg_hints,   # 반올림 전 값 — 정렬용, 반환 직전에 제거
        })
    # 평균 힌트가 높은(약한) 순, 반올림 때문에 동점이면 문제 수가 적은(연습 덜 된) 쪽을 우선한다.
    items.sort(key=lambda x: (-x["_avg_hints_raw"], x["problems_attempted"]))
    for item in items:
        del item["_avg_hints_raw"]
    return items


def get_overall_summary(user_id: int, grade: int | None = None, semester: int | None = None) -> dict:
    """전체 요약: 총 힌트 사용량 + 난이도별(쉬움/중간/어려움) 정답률 + 점수 기반 개인화 문장.

    단원별 숙련도와 달리, 여기서는 '전체 시도'(맞혔든 포기해서 공개했든)를 모두 센다 —
    정답률은 분모(시도)가 있어야 의미가 있기 때문이다.
    """
    query = get_client().table("attempts").select("difficulty, solved, hints_used").eq("user_id", user_id)
    if grade is not None:
        query = query.eq("grade", grade)
    if semester is not None:
        query = query.eq("semester", semester)
    rows = query.execute().data or []

    total_hints = sum(int(r.get("hints_used") or 0) for r in rows)
    by_diff: dict[str, list[bool]] = {d: [] for d in _DIFFICULTIES}
    for r in rows:
        diff = r.get("difficulty")
        if diff in by_diff:
            by_diff[diff].append(bool(r.get("solved")))

    accuracy = {
        diff: (round(100 * sum(results) / len(results), 1) if results else None)
        for diff, results in by_diff.items()
    }

    return {
        "total_attempts": len(rows),
        "total_hints_used": total_hints,
        "accuracy_by_difficulty": accuracy,
        "message": _personalized_message(accuracy, total_hints, len(rows)),
    }


def _personalized_message(accuracy: dict, total_hints: int, total_attempts: int) -> str:
    if total_attempts == 0:
        return "아직 기록이 없어요. 문제를 풀면 여기에 나만의 학습 리포트가 쌓여요!"

    easy, mid, hard = accuracy.get("쉬움"), accuracy.get("중간"), accuracy.get("어려움")
    known = [v for v in (easy, mid, hard) if v is not None]
    if not known:
        return "아직 난이도별 기록이 부족해요. 조금 더 풀어볼까요?"

    if hard is not None and easy is not None and hard - easy >= 15:
        parts = ["어려운 문제에서 응용력이 특히 좋아요! 쉬운 문제에서 방심하지 않도록 조심해봐요."]
    elif easy is not None and hard is not None and easy - hard >= 15:
        parts = ["기본기는 아주 튼튼해요! 어려운 문제에 조금씩 더 도전해봐요."]
    elif min(known) >= 80:
        parts = ["난이도에 상관없이 고르게 잘 풀고 있어요!"]
    else:
        parts = ["차근차근 실력이 쌓이고 있어요."]

    if total_attempts:
        avg_hints = total_hints / total_attempts
        if avg_hints < 0.5:
            parts.append("힌트를 거의 안 쓰고 스스로 척척 풀어내고 있어요!")
        elif avg_hints >= 2:
            parts.append("힌트를 꽤 많이 활용하고 있어요 — 조금 더 스스로 고민해보는 연습을 해봐요.")

    return " ".join(parts)
