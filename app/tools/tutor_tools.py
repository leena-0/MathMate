"""
핵심 Tool 구현.
Day3: Solar(LLM)가 있으면 실제 호출, 없거나 실패하면 Mock 규칙으로 자동 폴백.
바깥 시그니처(입출력)는 그대로라 그래프/노드는 안 바뀐다.
"""
import re
import logging
from app.schemas.chat import Hint, Diagnosis
from app.core import llm_client, prompts

log = logging.getLogger(__name__)

# --- Mock 폴백용 규칙 패턴 ---
_LEAK_PATTERNS = ["답 알려", "답만", "정답 뭐", "정답이 뭐", "그냥 알려", "풀어줘", "답 좀", "정답 알려", "답이 뭐"]
_OFFTOPIC_PATTERNS = ["게임", "놀자", "심심", "축구", "노래", "영화", "사랑", "점심", "뭐해", "재미없"]
_VALID_INTENTS = {"normal", "answer_seeking", "off_topic"}


def classify_intent(message: str) -> str:
    """의도 분류: normal | answer_seeking | off_topic (입력단 가드레일)."""
    data = llm_client.chat_json(prompts.INTENT_SYS, message)
    if data and data.get("intent") in _VALID_INTENTS:
        return data["intent"]
    # --- Mock 폴백 ---
    if any(p in message for p in _LEAK_PATTERNS):
        return "answer_seeking"
    if any(p in message for p in _OFFTOPIC_PATTERNS):
        return "off_topic"
    return "normal"


def diagnose_step(problem: dict, attempt: str) -> Diagnosis:
    """오답/막힌 지점 진단."""
    data = llm_client.chat_json(prompts.DIAGNOSE_SYS, prompts.diagnose_user(problem, attempt))
    if data is not None and "is_correct" in data:
        return Diagnosis(
            stuck_point=str(data.get("stuck_point", "")),
            is_correct=bool(data.get("is_correct")),
            solved=bool(data.get("solved")),
        )
    # --- Mock 폴백 (규칙 휴리스틱) ---
    ans = str(problem["answer"]).replace(" ", "")
    text = attempt.replace(" ", "")
    if ans in text and "묶음" not in text:
        return Diagnosis(stuck_point="", is_correct=True, solved=True)
    if "묶음" in text and ans in text:
        return Diagnosis(stuck_point="", is_correct=True, solved=False)
    return Diagnosis(stuck_point="나눗셈의 의미를 아직 못 잡음", is_correct=False, solved=False)


def generate_hint(problem: dict, hint_level: int) -> Hint:
    """hint_level(1~3)에 맞춘 소크라테스식 힌트. LLM 있으면 자연스럽게 생성, 없으면 데이터 힌트 사용."""
    level = max(1, min(hint_level, 3))
    ref = problem["hint_by_level"][str(level)]
    txt = llm_client.chat_text(prompts.HINT_SYS, prompts.hint_user(problem, ref, level))
    hint_text = txt.strip() if txt else ref
    return Hint(hint_text=hint_text, level=level, contains_answer=False)


def verify_no_leak(text: str, answer: str) -> bool:
    """출력단 가드레일: 정답 숫자가 응답에 '단독'으로 등장하면 위험(False)."""
    ans = str(answer).strip()
    return re.search(rf"(?<!\d){re.escape(ans)}(?!\d)", text) is None
