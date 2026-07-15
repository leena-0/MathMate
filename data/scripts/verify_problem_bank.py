"""
data/scripts/verify_problem_bank.py — 문제은행 단원 태깅 정확도 재검증.

build_problem_bank.py가 선별·태깅한 문제들이 실제로 그 단원의 핵심 개념(UNIT_GUIDE)과
맞는지 Solar로 다시 한 번 엄격하게 판정한다. 생성/선별 당시 잘못 태깅된 문제
(예: 약수와 배수 단원에 합집합 문제가 들어간 경우)를 찾아낸다.

실행 (프로젝트 루트, .env에 SOLAR_API_KEY):
  python data/scripts/verify_problem_bank.py
  python data/scripts/verify_problem_bank.py --file data/problems.json --workers 8
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from app.core import llm_client  # noqa: E402
from data.scripts.build_problem_bank import get_guide  # noqa: E402  (UNIT_GUIDE/GUIDE_OVERRIDE 재사용)

VERIFY_SYS = (
    "너는 초등 수학 교육과정 검수관이다. 문제가 [단원 개념 정의]와 '근본적으로 다른 수학 영역'을 "
    "다루는지만 판정한다 — 소재나 난이도 차이, 같은 개념의 응용된 형태는 무시한다.\n"
    "판정 기준:\n"
    "- matches=false: 문제를 풀 때 실제로 쓰는 핵심 수학 개념이 단원 정의와 아예 다른 분야다.\n"
    "  예) 단원은 '약수와 배수'인데 문제는 집합의 합집합/포함배제, 단원은 '큰 수'인데 문제는 "
    "순수 곱셈·나눗셈·단위변환 절차 문제, 단원은 '규칙과 대응'인데 문제는 경우의 수.\n"
    "- matches=true: 단원 정의가 다루는 개념을 실제로 사용해서 푸는 문제다. 같은 개념을 다른 소재나 "
    "응용된 형태로 묻는 것(예: '큰 수' 단원에서 숫자 카드로 큰 수를 만들어 비교하거나, 억 단위 "
    "수를 나누는 응용 문제)은 여전히 matches=true다 — 교과서에도 흔한 정상적인 응용 유형이다.\n"
    "애매하면 matches=true로 판정하라(불필요한 오탐으로 정상 문제를 지우면 안 된다).\n"
    '반드시 {"matches": true/false, "reason": "한 줄 설명"} 형태의 JSON만 출력하라.'
)


def _verify_one(p: dict) -> dict | None:
    guide = get_guide(p["grade"], p["semester"], p["unit"])
    user = (
        f"[단원] {p['unit']}\n[단원 개념 정의] {guide}\n"
        f"[문제] {p['problem']}\n[정답] {p['answer']}\n"
        "이 문제가 위 단원 개념 정의에 실제로 맞나요?"
    )
    data = llm_client.chat_json(VERIFY_SYS, user, trace_name="verify_unit_tag")
    if data is None or "matches" not in data:
        return None   # 호출 실패/파싱 실패 -> 재검증 필요 목록으로 표시
    return {
        "id": p["id"], "grade": p["grade"], "semester": p["semester"], "unit": p["unit"],
        "difficulty": p["difficulty"], "problem": p["problem"],
        "matches": bool(data.get("matches")), "reason": data.get("reason", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=os.path.join(ROOT, "data", "problems.json"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "tag_verification_report.json"))
    ap.add_argument("--limit", type=int, default=0, help="점검 대상 상한(0=전체, 빠른 점검용)")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as f:
        problems = json.load(f)
    if args.limit:
        problems = problems[:args.limit]

    print(f"검증 대상 {len(problems)}개 (workers={args.workers})")
    all_results, mismatches, failed_ids = [], [], []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_verify_one, p): p for p in problems}
        done = 0
        for fut in as_completed(futures):
            p = futures[fut]
            r = fut.result()
            done += 1
            if done % 25 == 0 or done == len(problems):
                print(f"  {done}/{len(problems)} (불일치 {len(mismatches)}건 발견)")
            if r is None:
                failed_ids.append(p["id"])
                continue
            all_results.append(r)
            if not r["matches"]:
                mismatches.append(r)

    mismatches.sort(key=lambda r: (r["grade"], r["semester"], r["unit"]))
    report = {
        "total": len(problems),
        "checked": len(all_results),
        "mismatch_count": len(mismatches),
        "failed_ids": failed_ids,
        "mismatches": mismatches,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {len(all_results)}개 판정, 불일치 {len(mismatches)}개, 호출실패 {len(failed_ids)}개")
    print(f"리포트 저장: {args.out}")


if __name__ == "__main__":
    main()
