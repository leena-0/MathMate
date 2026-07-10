# MathMate 🧮

> 정답을 알려주지 않고 힌트로만 유도하는 초등 수학 소크라테스식 튜터

가천대 AI 부트캠프 · 생성형AI 고급과정 프로젝트
팀원: 권지운, 이나영

## 소개

MathMate는 초등학교 4~6학년 학생을 대상으로 하는 대화형 수학 튜터입니다.
일반적인 AI 튜터와 달리 **정답을 직접 알려주지 않고**, 학생이 틀려도
힌트와 되질문으로만 스스로 답에 도달하도록 유도합니다.

- **답 유출 방지 가드레일**: 최종 정답을 노출하지 않고, "답만 알려줘" 같은 우회 요청도 차단
- **단계적 힌트**: 막힌 지점을 진단해 다음 한 걸음만 유도
- **진척도 추적**: 정답률이 아니라 "힌트 사용량"으로 단원별 숙련도를 측정

## 기술 스택

- **Agent**: LangGraph
- **Backend**: FastAPI + SSE (스트리밍)
- **LLM**: Solar API
- **DB**: PostgreSQL (진척도·체크포인트)
- **평가**: DeepEval
- **배포**: Docker + GCP Compute Engine + GitHub Actions

## 데이터

- 출처: [kuotient/orca-math-word-problems-193k-korean](https://huggingface.co/datasets/kuotient/orca-math-word-problems-193k-korean) (CC-BY-SA-4.0)
- 초등 4~6학년 문장제에서 선별 → 단원·난이도 라벨링 → 단계별 힌트 보강

## 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/leena-0/MathMate.git
cd MathMate

# 2. 가상환경 + 의존성
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경변수 설정 (.env)
cp .env.example .env            # UPSTAGE_API_KEY 등 채우기

# 4. 실행
uvicorn app.main:app --reload

# 5. 동작 확인
curl http://localhost:8000/api/health
```

## 환경변수

| 변수 | 설명 |
|---|---|
| `UPSTAGE_API_KEY` | Solar API 키 |
| `DATABASE_URL`  | PostgreSQL 접속 URL |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | (선택) LLM 호출 트레이싱. 비워두면 비활성 |

## 프로젝트 구조

```
app/
├── main.py          FastAPI 진입점 (/api/health)
├── api/             라우터 (chat, problems, session)
├── agent/           LangGraph State/Node/Graph
├── tools/           진단·힌트생성·유출검증 도구
├── schemas/         Pydantic 모델
└── db/              PostgreSQL 모델
data/                문제은행 JSON
tests/               pytest
```

---

## Day 2 진행 상태 (Mock 기반 MVP)

- ✅ Layered Architecture: `agent`(그래프) · `tools`(도구) · `repositories`(문제은행) · `api` · `schemas` · `db`
- ✅ Pydantic Tool Schema: `Hint`, `Diagnosis` + State(`agent/state.py`)
- ✅ LangGraph ReAct 루프: `intent_classify → (refuse | diagnose → hint/praise/final) → leak_verify`
- ✅ Mock LLM 로직(`tools/tutor_tools.py`)으로 핵심 시나리오 1개 성공
- ✅ 테스트 통과: `pytest -q` → 6 passed (health 1 + 소크라테스 시나리오 5)

```bash
pytest -q          # 6 passed
python run_demo.py # FE 스케치 대화 재현
```

### Day 3 예정
`tools/tutor_tools.py`의 Mock 규칙 → Solar API 호출로 교체, `api/chat.py` SSE 토큰 스트리밍 실제 구현.

## 배포 (Docker Compose + GCE)

### 로컬에서 컨테이너로 실행

```bash
cp .env.example .env   # UPSTAGE_API_KEY 등 채우기
docker compose up -d --build
# API:      http://localhost:8000
# Frontend: http://localhost:8501
```

### GCE VM 배포 (최초 1회, 수동)

1. GCE VM에 Docker + Docker Compose 플러그인 설치
2. 방화벽에서 8000, 8501 포트 열기
3. VM에 저장소 clone 후 `.env` 파일 생성 (실제 키 값 채우기 — git에는 올라가지 않음)
4. `docker compose up -d --build`로 최초 기동

### GitHub Actions CI/CD

- `ci.yml`: main/PR push마다 `pytest` 자동 실행
- `cd.yml`: CI 성공 후 main에 한해 3단계로 자동 배포
  1. **Build & Push to GHCR**: API/Frontend 이미지를 빌드해 `ghcr.io/leena-0/mathmate-{api,frontend}`에 push (태그: `latest` + 커밋 SHA)
  2. **Deploy to Compute Engine**: SSH로 GCE VM 접속 → `git pull`(compose 설정 갱신용) → GHCR 로그인 → `docker compose pull && docker compose up -d` (VM에서 재빌드하지 않고 미리 빌드된 이미지만 받아서 기동)
  3. **Deployment Summary**: 배포된 API 헬스체크 + 배포 URL을 Actions 요약에 기록

CD를 쓰려면 저장소 Settings → Secrets and variables → Actions에 아래를 등록해야 한다.

| Secret/Variable | 설명 |
|---|---|
| `GCE_HOST` | VM 외부 IP |
| `GCE_USER` | SSH 접속 계정 |
| `GCE_SSH_KEY` | SSH 개인키 |
| `GCE_DEPLOY_PATH` (변수, 선택) | VM 위의 저장소 경로, 기본값 `~/MathMate` |

## LLMOps 운영 안정성

- **Retry·Fallback**: Solar 호출 실패(429/5xx/타임아웃) 시 LiteLLM이 자동 재시도(`LLM_NUM_RETRIES`), 그래도 실패하면 대체 모델(`FALLBACK_MODEL`) 또는 Mock 규칙으로 폴백. 에러 유형(인증/요청한도/타임아웃/서버오류)별로 로그를 구분해 남긴다 (`app/core/llm_client.py`).
- **Langfuse Trace**: `LANGFUSE_*` 키를 설정하면 모든 Solar 호출(프롬프트·응답·지연시간·에러)이 Langfuse 대시보드에 `intent_classify`/`diagnose_step`/`generate_hint` 단위로 트레이싱된다. `litellm`과의 호환성 때문에 `langfuse<3`(v2 SDK) 고정 필요.
