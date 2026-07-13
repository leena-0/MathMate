"""환경설정 — Solar/LLM 키·모델·타임아웃. 키가 없으면 USE_LLM=False → Mock 규칙으로 폴백."""

try:
    from dotenv import load_dotenv
    load_dotenv()   # 프로젝트 루트의 .env 자동 로드
except ImportError:
    pass

import os

# SOLAR_API_KEY 우선, 없으면 UPSTAGE_API_KEY 도 허용
SOLAR_API_KEY = os.getenv("SOLAR_API_KEY") or os.getenv("UPSTAGE_API_KEY") or ""
SOLAR_MODEL = os.getenv("SOLAR_MODEL", "solar-pro2")
SOLAR_BASE_URL = os.getenv("SOLAR_BASE_URL", "https://api.upstage.ai/v1/solar")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "")          # 예: "gemini/gemini-2.0-flash"
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))          # 무한 대기 방지
LLM_NUM_RETRIES = int(os.getenv("LLM_NUM_RETRIES", "2"))   # 일시적 오류 재시도

USE_LLM = bool(SOLAR_API_KEY)   # 키가 있으면 실제 Solar, 없으면 Mock

# Langfuse — LLM 호출 트레이싱(LLMOps 운영 안정성 개선). 키 없으면 비활성.
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# Supabase — 진척도(users/attempts) 저장용 REST 클라이언트. 키 없으면 비활성.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_KEY)
