"""핵심 Tool stub. Day2~3에 실제 구현."""
from app.schemas.chat import Hint, Diagnosis


def classify_intent(message: str) -> str:
    """답 유출 시도/주제 이탈 감지. returns: normal|answer_seeking|off_topic"""
    # TODO(Day3)
    return "normal"


def diagnose_step(problem: str, attempt: str) -> Diagnosis:
    """오답/막힌 지점 진단."""
    # TODO(Day2)
    return Diagnosis(stuck_point="", is_correct=False)


def generate_hint(problem: str, diagnosis: str, hint_level: int) -> Hint:
    """단계별 힌트 생성 (Solar API)."""
    # TODO(Day3)
    return Hint(hint_text="", level=hint_level, contains_answer=False)


def verify_no_leak(hint: str, answer: str) -> bool:
    """정답 유출 여부 판정. True면 안전."""
    # TODO(Day3): 최소한 answer 문자열이 hint에 직접 포함됐는지부터 체크
    return answer not in hint
