"""LangGraph 그래프 조립 및 실행. Day2~3에 완성."""
from app.schemas.chat import ChatRequest

# TODO(Day2): StateGraph 로 intent_classify → diagnose →
#   generate_hint → leak_verify → (재생성 or 응답) 라우팅 구성


async def run_tutor(req: ChatRequest):
    """튜터 실행 (async generator). 현재는 stub."""
    # TODO(Day3): 그래프 실행 결과를 토큰 단위로 yield
    yield "아직 구현되지 않았어요 (stub)."
