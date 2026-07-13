"""문제은행 로더 (사서 계층). Day2=JSON, Day5=DB로 교체 예정.
data/problems.sample.json(테스트·데모용 소량) + data/problems.json(생성된 대량, 있으면)을 합쳐 로드한다.
"""
import json
from pathlib import Path

_DIR = Path(__file__).resolve().parents[2] / "data"


def _load() -> list[dict]:
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


_PROBLEMS: list[dict] = _load()


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
    return [p for p in _PROBLEMS if _matches(p, unit, difficulty, grade, semester)]


def list_semesters(grade: int | None = None) -> list[int]:
    """주어진 학년(없으면 전체)에 실제로 존재하는 학기 목록."""
    return sorted({p["semester"] for p in _PROBLEMS
                   if p.get("semester") is not None and (not grade or p.get("grade") == grade)})


def list_units(grade: int | None = None, semester: int | None = None) -> list[str]:
    """주어진 학년·학기(없으면 전체)에 실제로 존재하는 단원 목록."""
    return sorted({p["unit"] for p in _PROBLEMS
                   if (not grade or p.get("grade") == grade)
                   and (not semester or p.get("semester") == semester)})
