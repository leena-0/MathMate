"""문제은행 로더 (사서 계층).

우선순위: Supabase(problems 테이블) → 없으면 로컬 JSON(problems.sample.json + problems.json).
- 앱 시작 시 한 번 메모리에 적재해 빠르게 조회한다.
- get_problem()은 정답 포함 '전체'를 반환한다(서버 내부·에이전트 전용).
- list_problems_public()은 정답/힌트/풀이를 뺀 '안전 뷰'를 반환한다(프론트/API 노출용).
  → 답 유출률 0% KPI를 위해 정답은 절대 클라이언트로 나가지 않는다.
"""
import json
import logging
from pathlib import Path

from app.core import config
from app.repositories import supabase_client

log = logging.getLogger(__name__)
_DIR = Path(__file__).resolve().parents[2] / "data"

# 프론트/외부에 내보내도 안전한 필드만
_PUBLIC_FIELDS = ("id", "grade", "semester", "unit", "difficulty", "problem")


def _from_supabase() -> list[dict]:
    """Supabase problems 테이블을 JSON과 동일한 형태(dict)로 변환해 로드. 실패 시 빈 리스트."""
    client = supabase_client.get_client()
    if client is None:
        return []
    try:
        rows, start, page = [], 0, 1000
        while True:                          # 1000행 페이지네이션(기본 상한 회피)
            res = client.table("problems").select("*").range(start, start + page - 1).execute()
            batch = res.data or []
            rows.extend(batch)
            if len(batch) < page:
                break
            start += page
        out = []
        for r in rows:
            out.append({
                "id": r["id"], "grade": r.get("grade"), "semester": r.get("semester"),
                "unit": r.get("unit"), "difficulty": r.get("difficulty"),
                "problem": r["problem"], "answer": str(r.get("answer", "")),
                "solution_steps": r.get("solution_steps") or [],
                "hint_by_level": {"1": r.get("hint1", ""), "2": r.get("hint2", ""), "3": r.get("hint3", "")},
                "next_question": r.get("next_question", ""), "source": r.get("source", ""),
            })
        return out
    except Exception as e:
        log.warning("Supabase 문제 로드 실패 → 로컬 JSON 폴백: %s", e)
        return []


def _from_json() -> list[dict]:
    problems: list[dict] = []
    seen: set = set()
    for name in ("problems.sample.json", "problems.json"):
        path = _DIR / name
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for p in json.load(f):
                pid = p.get("id")
                if pid in seen:
                    continue
                seen.add(pid)
                problems.append(p)
    return problems


def _load() -> list[dict]:
    if config.USE_SUPABASE:
        rows = _from_supabase()
        if rows:
            log.info("문제은행: Supabase에서 %d개 로드", len(rows))
            return rows
        log.warning("문제은행: Supabase 비어있음/실패 → 로컬 JSON 사용")
    return _from_json()


_PROBLEMS: list[dict] = _load()


def reload() -> int:
    """적재 후 재조회가 필요할 때 메모리 캐시를 갱신한다."""
    global _PROBLEMS
    _PROBLEMS = _load()
    return len(_PROBLEMS)


def _matches(p: dict, unit=None, difficulty=None, grade=None, semester=None) -> bool:
    if unit and p["unit"] != unit:
        return False
    if difficulty and p["difficulty"] != difficulty:
        return False
    if grade and p.get("grade") != grade:
        return False
    if semester and p.get("semester") != semester:
        return False
    return True


def get_problem(problem_id: str | None = None, unit: str | None = None, difficulty: str | None = None,
                grade: int | None = None, semester: int | None = None) -> dict:
    for p in _PROBLEMS:
        if problem_id and p["id"] != problem_id:
            continue
        if _matches(p, unit, difficulty, grade, semester):
            return p
    return _PROBLEMS[0]


def list_problems(unit: str | None = None, difficulty: str | None = None,
                   grade: int | None = None, semester: int | None = None) -> list[dict]:
    """내부용: 전체 필드 포함(정답 포함). API로 그대로 내보내지 말 것."""
    return [p for p in _PROBLEMS if _matches(p, unit, difficulty, grade, semester)]


def list_problems_public(unit: str | None = None, difficulty: str | None = None,
                          grade: int | None = None, semester: int | None = None) -> list[dict]:
    """외부용: 정답·힌트·풀이를 제외한 안전 뷰."""
    return [{k: p.get(k) for k in _PUBLIC_FIELDS}
            for p in list_problems(unit, difficulty, grade, semester)]


def list_semesters(grade: int | None = None) -> list[int]:
    """주어진 학년(없으면 전체)에 실제로 존재하는 학기 목록."""
    return sorted({p["semester"] for p in _PROBLEMS
                   if p.get("semester") is not None and (not grade or p.get("grade") == grade)})


def list_units(grade: int | None = None, semester: int | None = None) -> list[str]:
    """주어진 학년·학기(없으면 전체)에 실제로 존재하는 단원 목록."""
    return sorted({p["unit"] for p in _PROBLEMS
                   if (not grade or p.get("grade") == grade)
                   and (not semester or p.get("semester") == semester)})
