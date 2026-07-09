"""
핵심 Tool 구현 (Day2 = Mock 규칙 기반).
Day3에서 각 함수 내부만 Solar API 호출(구조화 출력)로 교체하면
바깥 시그니처가 같아 그래프/노드는 그대로 동작한다.
"""
import re
from app.schemas.chat import Hint, Diagnosis

# 학생이 답을 그냥 달라고 조르는 표현 (우회 요청 감지)
_LEAK_PATTERNS = ["답 알려", "답만", "정답 뭐", "정답이 뭐", "그냥 알려", "풀어줘", "답 좀", "정답 알려", "답이 뭐"]


def classify_intent(message: str) -> str:
    """returns: normal | answer_seeking | off_topic"""
    if any(p in message for p in _LEAK_PATTERNS):
        return "answer_seeking"
    return "normal"


def diagnose_step(problem: dict, attempt: str) -> Diagnosis:
    """오답/막힌 지점 진단 (Mock 휴리스틱; Day3 Solar가 일반화)."""
    ans = str(problem["answer"]).replace(" ", "")
    text = attempt.replace(" ", "")
    if ans in text and "묶음" not in text:          # 최종 정답
        return Diagnosis(stuck_point="", is_correct=True, solved=True)
    if "묶음" in text and ans in text:              # 중간 단계 정답
        return Diagnosis(stuck_point="", is_correct=True, solved=False)
    return Diagnosis(stuck_point="나눗셈의 의미를 아직 못 잡음", is_correct=False, solved=False)


def generate_hint(problem: dict, hint_level: int) -> Hint:
    """hint_level(1~3)에 맞춰 다음 한 걸음 힌트."""
    level = max(1, min(hint_level, 3))
    return Hint(hint_text=problem["hint_by_level"][str(level)], level=level, contains_answer=False)


def verify_no_leak(text: str, answer: str) -> bool:
    """정답 유출 여부 판정. True=안전.
    정답 숫자가 응답에 '단독'으로 등장하면 위험 (45의 5 같은 건 통과)."""
    ans = str(answer).strip()
    return re.search(rf"(?<!\d){re.escape(ans)}(?!\d)", text) is None
