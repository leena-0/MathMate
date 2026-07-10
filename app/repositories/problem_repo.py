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


def get_problem(problem_id: str | None = None, unit: str | None = None,
                difficulty: str | None = None) -> dict:
    for p in _PROBLEMS:
        if problem_id and p["id"] != problem_id:
            continue
        if unit and p["unit"] != unit:
            continue
        if difficulty and p["difficulty"] != difficulty:
            continue
        return p
    return _PROBLEMS[0]


def list_problems(unit: str | None = None, difficulty: str | None = None) -> list[dict]:
    return [p for p in _PROBLEMS
            if (not unit or p["unit"] == unit) and (not difficulty or p["difficulty"] == difficulty)]
