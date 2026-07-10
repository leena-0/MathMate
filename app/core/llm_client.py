"""
Solar LLM 클라이언트 (LiteLLM 게이트웨이).
- 키가 없으면 호출하지 않고 None 반환 → 호출부가 Mock 규칙으로 폴백.
- 타임아웃·Retry·Fallback 내장, JSON이 아닌 응답도 최대한 복구.
Day5: 여기 앞단에 LiteLLM 요청 가드레일(입력 필터)을 추가할 수 있음.
"""
import json
import logging
import re
from app.core import config

log = logging.getLogger(__name__)


def is_enabled() -> bool:
    return config.USE_LLM


def _call(system: str, user: str, temperature: float, json_mode: bool):
    """LiteLLM으로 Solar 호출. 실패 시 예외를 그대로 올린다(상위에서 처리)."""
    import litellm  # 지연 임포트: 키 없는 환경/테스트에선 불필요

    kwargs = dict(
        model=f"openai/{config.SOLAR_MODEL}",
        api_base=config.SOLAR_BASE_URL,
        api_key=config.SOLAR_API_KEY,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        timeout=config.LLM_TIMEOUT,
        num_retries=config.LLM_NUM_RETRIES,   # 429·5xx·타임아웃 자동 재시도(지수 백오프)
    )
    if config.FALLBACK_MODEL:
        kwargs["fallbacks"] = [config.FALLBACK_MODEL]   # 메인 실패 시 대체 모델
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = litellm.completion(**kwargs)
    return resp.choices[0].message.content


def chat_json(system: str, user: str) -> dict | None:
    """구조화(JSON) 응답을 dict로 반환. 비활성/실패/파싱불가 시 None."""
    if not config.USE_LLM:
        return None
    try:
        content = _call(system, user, temperature=0.0, json_mode=True)
        return _safe_json(content)
    except Exception as e:   # 인증(401)·잘못된요청(400)·서버오류(5xx)·타임아웃 등
        log.warning("Solar JSON 호출 실패 → Mock 폴백: %s", e)
        return None


def chat_text(system: str, user: str) -> str | None:
    """자유 텍스트 응답. 비활성/실패 시 None."""
    if not config.USE_LLM:
        return None
    try:
        return _call(system, user, temperature=0.4, json_mode=False)
    except Exception as e:
        log.warning("Solar 텍스트 호출 실패 → 기본 힌트 폴백: %s", e)
        return None


def _safe_json(text: str | None):
    """모델이 JSON이 아닌 잡텍스트(코드블록 등)를 섞어 줘도 최대한 복구."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)   # 본문 속 첫 JSON 객체 추출
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                return None
    return None
