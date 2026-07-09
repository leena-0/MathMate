"""서비스 계층 — 튜터 한 턴을 처리하는 절차를 조율한다."""
from app.schemas.chat import ChatRequest
from app.agent.graph import run_tutor


async def handle_turn(req: ChatRequest):
    """튜터 한 턴 처리 오케스트레이션. agent 실행 결과를 그대로 스트리밍한다."""
    # TODO(Day5): 여기서 진척도(student_id, problem_id 단위) 저장 로직 연동
    async for chunk in run_tutor(req):
        yield chunk
