"""LangGraph State 정의."""
from typing import TypedDict


class TutorState(TypedDict):
    messages: list        # 대화 이력 (Sliding Window 적용 예정)
    problem: str          # 현재 문제
    answer: str           # 정답 (유출 검증용, 학생에게 노출 금지)
    student_attempt: str  # 학생의 최근 풀이/답
    intent: str           # normal | answer_seeking | off_topic
    diagnosis: str        # 막힌 지점/오답 원인
    hint_level: int       # 힌트 구체화 단계 (1~3)
    hint: str             # 생성된 힌트
    leak_check: bool      # 정답 유출 여부 검증 결과
