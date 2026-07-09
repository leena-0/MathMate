"""
LangGraph 조립 = 노드를 엣지로 연결해 ReAct 루프(판단→행동)를 만든다.

  START → intent_classify ─┬─(답 유출 시도)→ refuse_and_redirect ─┐
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
    b.add_node("diagnose", nodes.diagnose)
    b.add_node("generate_hint", nodes.generate_hint)
    b.add_node("praise_next", nodes.praise_next)
    b.add_node("final_praise", nodes.final_praise)
    b.add_node("leak_verify", nodes.leak_verify)

    b.add_edge(START, "intent_classify")
    b.add_conditional_edges("intent_classify", nodes.route_after_intent,
                            {"refuse": "refuse_and_redirect", "diagnose": "diagnose"})
    b.add_conditional_edges("diagnose", nodes.route_after_diagnose,
                            {"final": "final_praise", "praise": "praise_next", "hint": "generate_hint"})
    for n in ["refuse_and_redirect", "final_praise", "praise_next", "generate_hint"]:
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
    """SSE용 async generator. Mock 단계: 최종 응답을 글자 단위로 스트리밍한다."""
    problem = problem_repo.get_problem(req.problem_id)
    out = tutor_turn(problem, req.message)
    response = out["response"]
    # TODO(Solar 연동): tutor_turn을 Solar 스트리밍 API 호출로 교체하고,
    # 여기서 LLM이 실제로 생성하는 토큰을 그대로 yield하도록 변경
    for ch in response:
        yield ch
        await asyncio.sleep(0.02)  # Mock에서 실시간 스트리밍처럼 보이게 하는 딜레이
