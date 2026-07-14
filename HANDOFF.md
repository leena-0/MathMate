# MathMate 작업 현황 (Claude Code 인수인계용)

> 이 문서 하나로 현재 상태를 파악하고 이어서 작업할 수 있도록 정리한 핸드오프 노트입니다.
> 최종 수정: 2026-07-13

---

## 1. 프로젝트 개요

**MathMate** — 초등 고학년(4~6학년) 대상 **소크라테스식 수학 튜터 에이전트**.

- **핵심 원칙**: 튜터는 **절대 최종 정답을 알려주지 않는다.** 단계별 힌트와 되질문(Socratic questioning)만 제공.
- **최우선 KPI**: **답 유출률 0%** (강력한 답 유출 가드레일).
- **진척도 측정**: 정답률이 아니라 **힌트 사용량**으로 학습 진행을 본다.
- **팀**: 권지운 / 이나영(GitHub: leena-0). Gachon University AI 부트캠프.
- **기간**: Day1~Day7 (7/8~7/16).

### 기술 스택
- **에이전트**: LangGraph (StateGraph, ReAct 루프, 조건부 엣지) + Pydantic Tool Schema
- **API**: FastAPI + SSE 스트리밍 (sse-starlette) — *검증 후 스트리밍* 방식(전체 응답을 가드레일로 검증한 뒤 토큰 스트리밍)
- **LLM**: Upstage Solar (`solar-pro2`) via LiteLLM 게이트웨이 (retry/fallback/timeout). 키 없으면 Mock 폴백.
- **프론트**: Streamlit (팀원 담당, `frontend/app.py`)
- **DB**(Day5 예정): PostgreSQL/Supabase (진척도·체크포인터)
- **배포**(Day4 예정): Docker / GCP / CI
- **평가**(Day5 예정): DeepEval

---

## 2. 아키텍처 (Layered Architecture)

요청 흐름: **api → service → agent → tools/llm_client**

```
app/
  api/          # FastAPI 라우터 (/api/problems, /api/chat SSE)
  service/      # 유스케이스 조합
  agent/        # graph.py(ReAct 그래프), nodes.py, state.py
  tools/        # tutor_tools.py (classify_intent, diagnose_step, generate_hint, verify_no_leak)
  schemas/      # Pydantic 모델
  core/         # config.py, llm_client.py, prompts.py
  repositories/ # 문제은행 로드 등
  db/           # (Day5)
data/
  problems.json                    # 앱이 실제 사용하는 문제은행 (clean)
  elementary_math_problems.csv     # 사람 검수용 (엑셀 안전 처리됨)
  scripts/build_problem_bank.py    # 문제은행 구축 파이프라인 ★현재 집중 작업
frontend/app.py                    # Streamlit UI
tests/                             # pytest (conftest가 USE_LLM=False 강제)
.env                               # (gitignored) 실제 키 보관
```

### 가드레일 이중화
- **입력**: `classify_intent(message, problem)` → normal / answer_seeking / off_topic
- **출력**: `verify_no_leak` — 응답에 정답이 새면 차단

---

## 3. 현재까지 완료된 것

- Day1~Day3 산출물(기획서, 회고, 아키텍처 스케치 등) 제출 완료
- 팀원 저장소를 base로 로직 이식·스키마 통일 → GitHub main 병합 완료
- Solar 연동 + 견고한 에러처리 (`app/core/llm_client.py`, 에러 유형별 로깅 `_log_failure`)
- 가드레일 이중화(입력/출력)
- SSE 토큰 스트리밍(검증 후 스트리밍)
- pytest 통과 (10개 테스트)
- **데이터 파이프라인**: orca-math(HF)에서 선별 + 부족분 Solar 생성 (아래 상세)

---

## 4. ★ 현재 집중 작업: 데이터 파이프라인

**파일**: `data/scripts/build_problem_bank.py` (모든 로직을 이 파일 하나로 통합. 별도 스크립트 만들지 말 것.)

### 하는 일
1. **Phase A (선별)**: `kuotient/orca-math-word-problems-193k-korean`(HF)를 훑어, 각 단원의 **개념 정의(UNIT_GUIDE)에 정확히 맞는 문제만** 선별.
2. **Phase B (생성)**: orca에 없는/부족한 단원·난이도를 Solar로 생성. 특히 **그림 필요 단원(FIGURE_DEPENDENT)**은 orca에 거의 없어 항상 생성.
3. 단원 순서대로 정렬 → `data/problems.json` + `data/elementary_math_problems.csv` 저장.

### 핵심 설계 포인트
- **`(학년, 학기, 단원)` 키로 관리** → 6-1 분수의 나눗셈(÷자연수)과 6-2 분수의 나눗셈(÷분수)을 별개로 취급.
- **UNIT_GUIDE + GUIDE_OVERRIDE**: 단원명만이 아니라 핵심 개념·주의(※제외 개념)를 태깅/생성 프롬프트에 주입해 오매핑 방지 (예: "규칙과 대응"에 경우의 수 문제 섞이는 것 방지). 개념 정의는 2022 개정 교육과정 기준으로 웹 검증함.
- **난이도 균형**: `--per-unit 30`이면 쉬움/중간/어려움 10/10/10.
- **검토(scan)와 LLM 태깅 분리** (최근 추가):
  - `--scan`: orca에서 **검토**할 문항 수 (값쌈, 네트워크 스트리밍).
  - LLM 태깅은 **목표 버킷이 차면 조기 종료(early-stop)** → scan을 키워도 태깅 비용은 안 늘어남.
  - **셔플 스트리밍**(`.shuffle(seed, buffer_size)`)으로 18만 개에서 골고루 샘플링.
  - 희귀 단원 때문에 무한히 도는 것 방지 위해 **정체 감지(STALL)** + `--max-tags` 상한.
- **엑셀 안전 처리**: 분수 답(5/4 등)이 엑셀에서 날짜로 변환되는 것 방지 → 검수 CSV에만 `="5/4"` 텍스트 고정. `problems.json` 원본은 그대로.
- **병렬**: `--workers`개 스레드로 LLM 호출 (병목은 API 네트워크 지연, 로컬 GPU 아님).

### 교육과정 (2022 개정, CURRICULUM 딕셔너리)
- 학기당 6단원, 총 **36단원**. `--per-unit 30`이면 **총 1,080문제**.
- 최근 수정: 6학년 2학기 맨 앞에 **분수의 나눗셈** 추가 (÷분수 개념).

### 실행 예시
```powershell
# 소량 점검
python data/scripts/build_problem_bank.py --grades 5 --per-unit 6 --scan 3000 --workers 8

# 전체 구축 (많이 훑되 태깅은 필요한 만큼만)
python data/scripts/build_problem_bank.py --grades 4,5,6 --per-unit 30 --scan 60000 --workers 8

# 선별만(생성 없이)
python data/scripts/build_problem_bank.py --grades 5 --per-unit 30 --scan 20000 --no-generate
```

주요 옵션: `--scan`(검토 수/값쌈) · `--max-tags`(태깅 호출 상한/비쌈, 0=무제한) · `--seed`(셔플 표본) · `--workers`(병렬) · `--no-generate`(선별만)

---

## 5. 실행 환경

- **Python 3.12** (venv). `str | None` 문법 때문에 3.9는 안 됨.
- 패키지: `uv pip install -r requirements.txt` (pyproject 없어서 `uv sync`는 안 됨)
- venv 활성화 후에는 `python -m pytest`, `python -m uvicorn ...` 사용 (`uv run`은 trampoline 오류남)
- **서버 실행**: `python -m uvicorn app.main:app --reload` → 프론트는 `streamlit run frontend/app.py`
- **`.env`** (gitignored, 저장소에 없음): `UPSTAGE_API_KEY`, `SOLAR_MODEL`, `SOLAR_BASE_URL`, `LLM_TIMEOUT`, `LLM_NUM_RETRIES`, `SUPABASE_URL`, `SUPABASE_KEY`. 새 환경에선 이 파일 직접 만들어야 함.
- 테스트: `python -m pytest` (conftest가 `USE_LLM=False`로 Mock 폴백 강제)

### 주의사항 / 과거 이슈
- OneDrive "온라인 전용" 파일 문제로 **bash가 하위 디렉터리 순회 실패**할 수 있음. Read/Write/Edit/Grep은 정상.
- git commit 메시지는 **단순 ASCII**로 (PowerShell에서 스마트따옴표/괄호가 `>>` 연속 입력 유발).
- main에 직접 push 금지 → 브랜치 → PR → 머지.

---

## 6. 남은 작업 (TODO)

1. **데이터 파이프라인 마무리**: 전체 구축(`--grades 4,5,6 --per-unit 30`) 실행 → CSV 검수(단원 매핑/난이도 분포/답 정상 여부) → `problems.json` 확정.
2. **problems.json 앱 연동**: `app/repositories`에서 로드해 `/api/problems`가 실제 문제은행을 쓰도록.
3. **Day4 배포**: Dockerfile, GCP 배포, CI 파이프라인.
4. **Day5**: PostgreSQL 진척도 저장 + LangGraph 체크포인터, DeepEval로 답 유출 0% 검증.

---

## 7. 최근 변경 요약 (이번 세션)

- CURRICULUM 6-2에 **분수의 나눗셈** 추가 (교육과정 웹 검증).
- `select_from_orca` 재설계: **검토(scan)와 태깅 분리** + 셔플 + 조기 종료(early-stop) + 정체 감지.
- 새 옵션 `--scan`(의미 변경: 검토 수), `--max-tags`, `--seed` 추가.
- 값싼 사전 필터 `_too_advanced`(중고교 문항 컷) 추가.
- 검수 CSV 엑셀 안전 처리(`_excel_safe`)로 분수 답이 날짜로 표시되는 문제 해결.
