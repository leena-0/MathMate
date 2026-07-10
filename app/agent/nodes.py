"""
LangGraph 노드 = 에이전트의 각 행동 단계.
원칙: 최종 정답은 학생이 먼저 말하기 전엔 절대 노출하지 않는다.
"""
from app.agent.state import TutorState
from app.tools import tutor_tools as tools


def intent_classify(state: TutorState) -> dict:
    return {"intent": tools.classify_intent(state["student_attempt"])}


def refuse_and_redirect(state: TutorState) -> dict:
    """답 유출 시도 → 정중히 거절 + 정답 대신 첫 힌트."""
    first_hint = state["problem"]["hint_by_level"]["1"]
    return {"response": f"답을 바로 알려주면 다음에 또 막혀요. 대신 같이 볼까요? {first_hint}",
            "hint_level": max(state.get("hint_level", 1), 1)}


def handle_off_topic(state: TutorState) -> dict:
    """주제 이탈(잡담) → 부드럽게 수학으로 유도."""
    return {"response": "우리 지금 수학 문제를 풀고 있어요! 먼저 이 문제부터 같이 풀어볼까요?"}


def diagnose(state: TutorState) -> dict:
    d = tools.diagnose_step(state["problem"], state["student_attempt"])
    return {"diagnosis": d.model_dump()}


def generate_hint(state: TutorState) -> dict:
    """아직 못 풀었을 때 → 다음 한 걸음 힌트."""
    level = state.get("hint_level", 1)
    h = tools.generate_hint(state["problem"], level)
    return {"response": h.hint_text, "hint": h.hint_text, "hint_level": min(level + 1, 3)}


def praise_next(state: TutorState) -> dict:
    return {"response": f"맞았어요! {state['problem']['next_question']}"}


def final_praise(state: TutorState) -> dict:
    return {"response": "정확해요! 스스로 끝까지 풀어냈네요. 정말 잘했어요!", "solved": True}


def leak_verify(state: TutorState) -> dict:
    """출력단 가드레일: 응답 직전 정답 유출 검사, 샜으면 가린다."""
    safe = tools.verify_no_leak(state.get("response", ""), str(state["problem"]["answer"]))
    if not safe:
        return {"response": "(정답을 바로 말하지 않을게요!) 다시 힌트로 가볼까요?", "leak_check": False}
    return {"leak_check": True}


# ----- 라우팅 -----
def route_after_intent(state: TutorState) -> str:
    it = state["intent"]
    if it == "answer_seeking":
        return "refuse"
    if it == "off_topic":
        return "offtopic"
    return "diagnose"


def route_after_diagnose(state: TutorState) -> str:
    d = state["diagnosis"]
    if d["solved"]:
        return "final"
    return "praise" if d["is_correct"] else "hint"
