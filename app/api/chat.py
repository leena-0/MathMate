"""튜터 대화 엔드포인트 (SSE 스트리밍). Day3에 실제 구현."""
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.schemas.chat import ChatRequest
from app.agent.graph import run_tutor

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    async def event_generator():
        # TODO(Day3): LangGraph 실행 결과를 토큰 단위로 SSE 전송
        async for chunk in run_tutor(req):
            yield {"data": chunk}
    return EventSourceResponse(event_generator())
