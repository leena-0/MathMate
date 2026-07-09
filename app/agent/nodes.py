"""LangGraph 노드 stub. Day2~3에 실제 로직 구현."""
from app.agent.state import TutorState


def intent_classify(state: TutorState) -> TutorState:
    # TODO(Day3): 답 유출 시도/주제 이탈 감지
    state["intent"] = "normal"
    return state


def diagnose(state: TutorState) -> TutorState:
    # TODO(Day2): 학생 풀이에서 막힌/틀린 지점 진단
    state["diagnosis"] = ""
    return state


def generate_hint(state: TutorState) -> TutorState:
    # TODO(Day3): hint_level에 맞춰 다음 한 걸음 힌트 생성 (Solar API)
    state["hint"] = ""
    return state


def leak_verify(state: TutorState) -> TutorState:
    # TODO(Day3): 힌트에 정답이 섞였는지 검증, 새면 재생성 라우팅
    state["leak_check"] = True
    return state


def refuse_and_redirect(state: TutorState) -> TutorState:
    # TODO(Day3): 정중히 거절하고 힌트 단계로 전환
    state["hint"] = "답을 바로 알려주면 다음에 또 막혀요. 첫 힌트만 같이 볼까요?"
    return state
