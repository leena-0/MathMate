"""
LangGraph 조립 = 노드를 엣지로 연결해 ReAct 루프를 만든다.

  START → intent_classify ─┬─(답 유출 시도)→ refuse_and_redirect ─┐
                           ├─(주제 이탈)→ handle_off_topic ────────┤
                           └─(정상)→ diagnose ─┬─(풀었음)→ final_praise ─┤
                                               ├─(중간정답)→ praise_next ─┤
                                               └─(막힘)→ generate_hint ───┤
                                        (모두)→ leak_verify → END ←────────┘
"""
import asyncio
from langgraph.graph import StateGraph, START, END
from app.agent.state import TutorState
from app.agent import nodes
from app.repositories import problem_repo
from app.schemas.chat import ChatRequest


def build_graph():
    b = StateGraph(TutorState)
    b.add_node("intent_classify", nodes.intent_classify)
    b.add_node("refuse_and_redirect", nodes.refuse_and_redirect)
    b.add_node("handle_off_topic", nodes.handle_off_topic)
    b.add_node("diagnose", nodes.diagnose)
    b.add_node("generate_hint", nodes.generate_hint)
    b.add_node("praise_next", nodes.praise_next)
    b.add_node("final_praise", nodes.final_praise)
    b.add_node("leak_verify", nodes.leak_verify)

    b.add_edge(START, "intent_classify")
    b.add_conditional_edges("intent_classify", nodes.route_after_intent,
                            {"refuse": "refuse_and_redirect",
                             "offtopic": "handle_off_topic",
                             "diagnose": "diagnose"})
    b.add_conditional_edges("diagnose", nodes.route_after_diagnose,
                            {"final": "final_praise", "praise": "praise_next", "hint": "generate_hint"})
    for n in ["refuse_and_redirect", "handle_off_topic", "final_praise", "praise_next", "generate_hint"]:
        b.add_edge(n, "leak_verify")
    b.add_edge("leak_verify", END)
    return b.compile()


GRAPH = build_graph()   # 한 번만 컴파일


def tutor_turn(problem: dict, message: str, hint_level: int = 1) -> dict:
    """대화 한 턴 실행 (테스트·데모·API 공용 진입점)."""
    state = {
        "problem": problem,
        "answer": str(problem["answer"]),
        "student_attempt": message,
        "hint_level": hint_level,
    }
    return GRAPH.invoke(state)


async def run_tutor(req: ChatRequest):
    """
    SSE 스트리밍용 async generator.
    핵심: 답 유출 방지 가드레일 때문에 '완성된 응답'을 leak_verify로 먼저 검증한 뒤,
    검증을 통과한 텍스트만 토큰(글자 조각) 단위로 흘려보낸다(빠른 타이핑 UX).
    """
    problem = problem_repo.get_problem(req.problem_id)
    out = tutor_turn(problem, req.message)
    text = out.get("response", "")

    chunk = ""
    for ch in text:
        chunk += ch
        if len(chunk) >= 2 or ch in " \n.,!?":
            yield chunk
            chunk = ""
            await asyncio.sleep(0.015)   # 타이핑 효과
    if chunk:
        yield chunk
