"""테스트는 API 키 유무와 상관없이 Mock 규칙으로 결정론적으로 실행 (네트워크 호출 방지)."""
import pytest
from app.core import config


@pytest.fixture(autouse=True)
def force_mock(monkeypatch):
    monkeypatch.setattr(config, "USE_LLM", False)
    # 테스트는 네트워크(Supabase) 없이 로컬 JSON으로만 결정론적으로 실행
    monkeypatch.setattr(config, "USE_SUPABASE", False)
