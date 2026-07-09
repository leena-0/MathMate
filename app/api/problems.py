"""문제은행 조회. Day1~2에 데이터 연결."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/problems")
def list_problems(unit: str | None = None, difficulty: str | None = None):
    # TODO(Day2): data/problems.json 에서 단원·난이도별 필터링
    return {"unit": unit, "difficulty": difficulty, "items": []}
