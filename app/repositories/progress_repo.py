"""학습 진척도 저장소 (Supabase progress 테이블).

핵심 KPI = '힌트 사용량'. 학생×문제 단위로 누적한다.
Supabase가 없으면(로컬/테스트) 조용히 무시하고 기록하지 않는다(앱 흐름을 막지 않음).
"""
import logging

from app.repositories import supabase_client

log = logging.getLogger(__name__)


def record_turn(student_id: str, problem_id: str, turn: dict) -> None:
    """튜터 한 턴 결과(turn=graph out)를 읽어 진척도를 누적 upsert한다.

    turn에서 추출:
      - hint_given: 이번 턴에 힌트를 줬는가 (out['hint'] 존재)
      - hint_level: 도달한 힌트 단계
      - solved   : 최종 정답 도달 여부
    실패해도 예외를 삼켜 대화 흐름을 막지 않는다.
    """
    client = supabase_client.get_client()
    if client is None or not student_id or not problem_id:
        return
    try:
        hint_given = bool(turn.get("hint"))
        hint_level = int(turn.get("hint_level") or 0)
        solved = bool(turn.get("solved")) or bool((turn.get("diagnosis") or {}).get("solved"))

        # 기존 행 읽어 누적(read-modify-write; 수업 데모 규모라 경쟁 무시)
        res = (client.table("progress").select("*")
               .eq("student_id", student_id).eq("problem_id", problem_id)
               .limit(1).execute())
        cur = (res.data or [{}])[0]

        row = {
            "student_id": student_id,
            "problem_id": problem_id,
            "attempts": int(cur.get("attempts", 0)) + 1,
            "hints_used": int(cur.get("hints_used", 0)) + (1 if hint_given else 0),
            "max_hint_level": max(int(cur.get("max_hint_level", 0)), hint_level),
            "solved": bool(cur.get("solved")) or solved,
        }
        client.table("progress").upsert(row, on_conflict="student_id,problem_id").execute()
    except Exception as e:
        log.warning("진척도 기록 실패(무시): %s", e)


def get_progress(student_id: str) -> list[dict]:
    """특정 학생의 문제별 진척도 목록."""
    client = supabase_client.get_client()
    if client is None:
        return []
    try:
        res = (client.table("progress").select("*")
               .eq("student_id", student_id).order("updated_at", desc=True).execute())
        return res.data or []
    except Exception as e:
        log.warning("진척도 조회 실패: %s", e)
        return []


def summary(student_id: str) -> dict:
    """학생 요약: 총 힌트 사용량·푼 문제 수 등(대시보드용)."""
    rows = get_progress(student_id)
    return {
        "student_id": student_id,
        "problems_attempted": len(rows),
        "problems_solved": sum(1 for r in rows if r.get("solved")),
        "total_hints_used": sum(int(r.get("hints_used", 0)) for r in rows),
    }
