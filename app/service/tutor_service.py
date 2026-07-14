"""서비스 계층 — 튜터 한 턴을 처리하는 절차를 조율한다."""
import logging
from app.schemas.chat import ChatRequest
from app.agent.graph import run_tutor
from app.core import config
from app.repositories import attempt_repo, progress_repo

log = logging.getLogger(__name__)


async def handle_turn(req: ChatRequest):
    """튜터 한 턴 처리 오케스트레이션. agent 실행 결과를 그대로 스트리밍하고,
    턴마다 힌트 사용량을, 문제를 풀어냈으면(solved) 단원별 숙련도를 기록한다."""
    state: dict = {}
    async for chunk in run_tutor(req, result_holder=state):
        yield chunk

    # 힌트 사용량 KPI 누적. Supabase 없으면 내부에서 조용히 무시된다.
    progress_repo.record_turn(req.student_id, req.problem_id, state)

    if config.SUPABASE_ENABLED and state.get("solved"):
        try:
            attempt_repo.record_attempt(
                user_id=int(req.student_id),
                problem_id=req.problem_id,
                unit=state.get("unit", ""),
                hints_used=state.get("hint_level", 1),
                solved=True,
                grade=state.get("grade"),
                semester=state.get("semester"),
            )
        except Exception as e:   # 진척도 저장 실패가 튜터 응답 자체를 막으면 안 됨
            log.warning("진척도 기록 실패(무시하고 계속 진행): %s", e)
