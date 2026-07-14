"""문제은행 조회."""
from fastapi import APIRouter
from app.repositories import problem_repo

router = APIRouter()


@router.get("/problems")
def list_problems(unit: str | None = None, difficulty: str | None = None):
    # 정답/힌트/풀이가 빠진 '안전 뷰'만 반환 (답 유출률 0% 보장)
    items = problem_repo.list_problems_public(unit, difficulty)
    return {"unit": unit, "difficulty": difficulty, "count": len(items), "items": items}
