"""
data/scripts/build_problem_bank.py

Hugging Face orca-math(한국어)에서 초등 고학년(4~6) 문장제를 선별하고,
Solar(LLM)로 [학년·학기·단원·난이도]를 자동 태깅 + 소크라테스식 힌트(hint_by_level)를 생성해
앱이 쓰는 data/problems.json 형식으로 저장한다. (사람 검수용 CSV도 함께 출력)

멘토링 반영:
- 난이도는 쎈수학 A/B/C 기준(A=쉬움, B=중간, C=어려움)을 프롬프트에 명시.
- "LLM 자동 태깅 → 사람 검수" 흐름: 결과를 review_problems.csv로 뽑아 사람이 검수 후 사용.

실행 (프로젝트 루트에서, .env에 SOLAR_API_KEY 필요):
  python data/scripts/build_problem_bank.py --dry-run          # HF 없이 내장 샘플 2개로 파이프라인·태깅 점검
  python data/scripts/build_problem_bank.py --keep 35 --scan 500   # 실제: 30~40개 구축
  # 나중에 대용량 확장: --keep 300 --scan 5000 처럼 숫자만 키우면 됨

의존성: datasets, litellm (requirements.txt)
"""
import argparse
import csv
import json
import logging
import os
import sys

# 프로젝트 루트를 import 경로에 추가 (python data/scripts/build_problem_bank.py 로 실행)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from app.core import llm_client  # noqa: E402  (LiteLLM Solar 래퍼: retry/fallback/타임아웃 내장)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("build_bank")

DATASET = "kuotient/orca-math-word-problems-193k-korean"
DATA_DIR = os.path.join(ROOT, "data")

# 초등 4~6학년 '문장제'에 잘 맞는 단원(연산/응용 위주). LLM이 이 중에서 고르거나 "기타".
UNITS = [
    "곱셈과 나눗셈", "큰 수", "규칙 찾기",
    "자연수의 혼합 계산", "약수와 배수", "규칙과 대응", "평균과 가능성",
    "분수의 덧셈과 뺄셈", "분수의 곱셈", "분수의 나눗셈",
    "소수의 덧셈과 뺄셈", "소수의 곱셈", "소수의 나눗셈",
    "비와 비율", "비례식과 비례배분",
]

TAG_SYS = (
    "너는 초등 수학 데이터 큐레이터다. 주어진 문장제(문제와 원본 풀이/정답)를 보고 "
    "초등 4~6학년 학습용으로 적합한지 판단하고 메타데이터를 붙여 JSON만 출력한다.\n\n"
    "[난이도 기준 — 쎈수학 A/B/C]\n"
    "- \"쉬움\"(A): 개념 확인·한 단계 단순 계산\n"
    "- \"중간\"(B): 두세 단계 계산이 필요한 응용 문장제\n"
    "- \"어려움\"(C): 여러 조건·심화 사고가 필요한 문제\n\n"
    "[단원] 아래 중 가장 알맞은 하나를 고르고, 없으면 \"기타\":\n"
    + ", ".join(UNITS) + "\n\n"
    "[출력 JSON 스키마]\n"
    "{\n"
    '  "usable": true/false,   // 초등 4~6 문장제로 적합? (범위 밖·오류·이상하면 false)\n'
    '  "grade": 4|5|6,\n'
    '  "semester": 1|2,\n'
    '  "unit": "<위 목록 중 하나 또는 기타>",\n'
    '  "difficulty": "쉬움"|"중간"|"어려움",\n'
    '  "problem": "<자연스러운 한국어로 정리한 문제 지문>",\n'
    '  "answer": "<최종 정답만 간단히. 예: 9명>",\n'
    '  "solution_steps": ["단계1", "단계2"],\n'
    '  "hint_by_level": {"1": "약한 힌트", "2": "중간 힌트", "3": "구체 힌트"},\n'
    '  "next_question": "정답 직전에 던질 유도 질문"\n'
    "}\n\n"
    "[절대 규칙] hint_by_level 과 next_question 에는 최종 정답(숫자·값)을 넣지 마라. JSON만 출력."
)


def tag_user(question: str, answer: str) -> str:
    return f"[문제]\n{question}\n\n[원본 풀이/정답]\n{answer}"


def _leak_free(rec: dict) -> bool:
    """힌트·유도질문에 정답이 새지 않았는지 확인."""
    ans = str(rec.get("answer", "")).strip()
    if not ans:
        return False
    texts = list(rec.get("hint_by_level", {}).values()) + [rec.get("next_question", "")]
    # 정답 문자열(또는 숫자부분)이 힌트에 직접 등장하면 유출로 간주
    num = "".join(ch for ch in ans if ch.isdigit())
    for t in texts:
        if ans and ans in t:
            return False
        if num and num in "".join(c for c in t if c.isdigit()):
            return False
    return True


def tag_one(question: str, answer: str) -> dict | None:
    """한 문항을 Solar로 태깅. 유효하지 않으면 None."""
    data = llm_client.chat_json(TAG_SYS, tag_user(question, answer))
    if not data or not data.get("usable"):
        return None
    try:
        grade = int(data["grade"])
        if grade not in (4, 5, 6):
            return None
        rec = {
            "grade": grade,
            "semester": int(data.get("semester", 1)),
            "unit": str(data["unit"]).strip(),
            "difficulty": str(data["difficulty"]).strip(),
            "problem": str(data["problem"]).strip(),
            "answer": str(data["answer"]).strip(),
            "solution_steps": list(data.get("solution_steps", [])),
            "hint_by_level": {str(k): str(v) for k, v in data.get("hint_by_level", {}).items()},
            "next_question": str(data.get("next_question", "")).strip(),
        }
    except (KeyError, ValueError, TypeError):
        return None
    if rec["difficulty"] not in ("쉬움", "중간", "어려움"):
        return None
    if not all(k in rec["hint_by_level"] for k in ("1", "2", "3")):
        return None
    if not rec["problem"] or not rec["answer"]:
        return None
    if not _leak_free(rec):
        log.info("  (스킵) 힌트에 정답 유출 → 제외")
        return None
    return rec


def iter_candidates(scan: int):
    """HF 데이터셋을 스트리밍하며 초등 문장제 후보만 걸러 (question, answer)를 내보낸다."""
    from datasets import load_dataset  # 지연 임포트 (dry-run 시 불필요)
    ds = load_dataset(DATASET, split="train", streaming=True)
    seen = 0
    for row in ds:
        if seen >= scan:
            break
        seen += 1
        q = (row.get("question") or row.get("instruction") or "").strip()
        a = str(row.get("answer") or row.get("output") or "").strip()
        if not q or not a:
            continue
        if len(q) > 300:                       # 너무 긴 문제 제외
            continue
        if not any(ch.isdigit() for ch in a):  # 수치 답이 없으면 제외
            continue
        yield q, a


DRY_SAMPLES = [
    ("사탕이 45개 있습니다. 한 사람에게 5개씩 나누어 주면 몇 명에게 줄 수 있나요?", "45 ÷ 5 = 9\n#### 9"),
    ("연필 3다스는 모두 몇 자루인가요? (1다스는 12자루입니다.)", "3 × 12 = 36\n#### 36"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=35, help="최종으로 남길 문항 수")
    ap.add_argument("--scan", type=int, default=500, help="훑어볼 후보 개수")
    ap.add_argument("--dry-run", action="store_true", help="HF 없이 내장 샘플로 점검")
    ap.add_argument("--out", default=os.path.join(DATA_DIR, "problems.json"))
    args = ap.parse_args()

    if not llm_client.is_enabled():
        log.error("SOLAR_API_KEY(.env)가 없어 태깅을 못 합니다. 키를 넣고 다시 실행하세요.")
        sys.exit(1)

    candidates = DRY_SAMPLES if args.dry_run else iter_candidates(args.scan)

    kept: list[dict] = []
    for i, (q, a) in enumerate(candidates, 1):
        rec = tag_one(q, a)
        if rec:
            rec["id"] = f"gen_{len(kept) + 1:04d}"
            kept.append(rec)
            log.info("[%d/%d] 채택: %s / %s / %s", len(kept), args.keep, rec["grade"], rec["unit"], rec["difficulty"])
        if len(kept) >= args.keep:
            break

    if not kept:
        log.error("채택된 문항이 없습니다. (키/모델/데이터 확인)")
        sys.exit(1)

    # 앱이 읽는 JSON
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    # 사람 검수용 CSV (Excel에서 열기)
    csv_path = os.path.join(DATA_DIR, "review_problems.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "grade", "semester", "unit", "difficulty", "problem", "answer",
                    "hint1", "hint2", "hint3", "next_question"])
        for r in kept:
            h = r["hint_by_level"]
            w.writerow([r["id"], r["grade"], r["semester"], r["unit"], r["difficulty"],
                        r["problem"], r["answer"], h.get("1", ""), h.get("2", ""), h.get("3", ""),
                        r["next_question"]])

    # 요약
    from collections import Counter
    log.info("\n=== 완료: %d문항 ===", len(kept))
    log.info("난이도: %s", dict(Counter(r["difficulty"] for r in kept)))
    log.info("단원   : %s", dict(Counter(r["unit"] for r in kept)))
    log.info("저장   : %s", args.out)
    log.info("검수용 : %s  ← 사람이 검수 후 사용하세요", csv_path)


if __name__ == "__main__":
    main()
