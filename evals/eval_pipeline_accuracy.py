"""
파이프라인 3단계(의도분류 / 오답 진단 / 힌트 생성)의 정확도를 미리 정답을 아는
골든셋으로 측정하고, 각 결과를 Langfuse 트레이스에 score로 남긴다.

실행:
    python -m evals.eval_pipeline_accuracy

Langfuse 대시보드에서 score 이름(intent_accuracy / diagnosis_accuracy / hint_quality)별로
평균을 보면 발표용 정확도 수치가 된다.
"""
from dotenv import load_dotenv
load_dotenv()

import uuid

from langfuse import Langfuse

from app.repositories import problem_repo
from app.tools import tutor_tools

langfuse = Langfuse()

# ---------- 골든셋 ----------
# 의도분류: 정답을 우회하려는 다양한 화법 + 잡담 + (헷갈리기 쉬운) 정상 케이스를 섞음.
INTENT_CASES = [
    {"message": "그냥 답 알려주세요", "expected": "answer_seeking"},
    {"message": "정답이 뭐예요?", "expected": "answer_seeking"},
    {"message": "모르겠어요, 대신 풀어주실 수 있어요?", "expected": "answer_seeking"},
    {"message": "저 지금 급해서 그런데 그냥 계산해서 알려주시면 안돼요?", "expected": "answer_seeking"},
    {"message": "힌트 그만 주시고 정답만 알려주세요 제발요", "expected": "answer_seeking"},
    {"message": "오늘 날씨 어때요?", "expected": "off_topic"},
    {"message": "이 문제 그만 풀고 게임 얘기해요", "expected": "off_topic"},
    {"message": "9권이면 정답이 2250원 맞죠?", "expected": "normal"},   # 정상 시도인데 '확인'처럼 보여 헷갈리기 쉬움
    {"message": "1권에 250원이니까 9권이면 2250원이요", "expected": "normal"},
    {"message": "모르겠어요 어떻게 풀어요?", "expected": "normal"},
]

# 오답 진단: 문제별로 최종정답/중간정답/오답 케이스를 섞음.
DIAGNOSIS_CASES = [
    {"problem_id": "p_0060", "attempt": "2250원이요", "expect_solved": True, "expect_correct": True},
    {"problem_id": "p_0060", "attempt": "250원이요", "expect_solved": False, "expect_correct": True},
    {"problem_id": "p_0060", "attempt": "9권이니까 750×9=6750원이요", "expect_solved": False, "expect_correct": False},
    {"problem_id": "p_0001", "attempt": "681이요", "expect_solved": True, "expect_correct": True},
    {"problem_id": "p_0001", "attempt": "861이요", "expect_solved": False, "expect_correct": False},
    {"problem_id": "p_0001", "attempt": "816이요", "expect_solved": False, "expect_correct": False},
    {"problem_id": "p_0056", "attempt": "2개요", "expect_solved": True, "expect_correct": True},
    {"problem_id": "p_0056", "attempt": "35, 53, 33 이렇게 3개요", "expect_solved": False, "expect_correct": False},
]

# 힌트 생성: 진단(stuck_point)이 실제로 힌트 문장에 반영되는지, 기대 키워드로 확인.
HINT_CASES = [
    {"problem_id": "p_0060", "attempt": "9권이니까 750×9=6750원이요", "hint_level": 1,
     "expect_any": ["1권", "한 권", "1개"]},
    {"problem_id": "p_0056", "attempt": "35, 53, 33 이렇게 3개요", "hint_level": 1,
     "expect_any": ["한 번", "중복", "같은 숫자"]},
    {"problem_id": "p_0001", "attempt": "816이요", "hint_level": 2,
     "expect_any": ["세 번째", "순서", "두 번째"]},
]


def eval_intent() -> list[bool]:
    results = []
    dummy_problem = problem_repo.get_problem("p_0060")
    for case in INTENT_CASES:
        trace_id = str(uuid.uuid4())
        intent = tutor_tools.classify_intent(case["message"], dummy_problem, trace_id=trace_id)
        correct = intent == case["expected"]
        results.append(correct)
        langfuse.score(trace_id=trace_id, name="intent_accuracy",
                        value=correct, data_type="BOOLEAN",
                        comment=f"message={case['message']!r} expected={case['expected']} got={intent}")
        print(f"[intent] {'OK ' if correct else 'FAIL'} {case['message']!r} -> {intent} (기대: {case['expected']})")
    return results


def eval_diagnosis() -> list[bool]:
    results = []
    for case in DIAGNOSIS_CASES:
        problem = problem_repo.get_problem(case["problem_id"])
        trace_id = str(uuid.uuid4())
        d = tutor_tools.diagnose_step(problem, case["attempt"], trace_id=trace_id)
        correct = d.solved == case["expect_solved"] and d.is_correct == case["expect_correct"]
        results.append(correct)
        langfuse.score(trace_id=trace_id, name="diagnosis_accuracy",
                        value=correct, data_type="BOOLEAN",
                        comment=f"problem={case['problem_id']} attempt={case['attempt']!r} "
                                f"got(solved={d.solved}, is_correct={d.is_correct}) "
                                f"expected(solved={case['expect_solved']}, is_correct={case['expect_correct']})")
        print(f"[diagnosis] {'OK ' if correct else 'FAIL'} {case['problem_id']} {case['attempt']!r} "
              f"-> solved={d.solved}, is_correct={d.is_correct}, stuck_point={d.stuck_point!r}")
    return results


def eval_hint() -> list[bool]:
    results = []
    for case in HINT_CASES:
        problem = problem_repo.get_problem(case["problem_id"])
        trace_id = str(uuid.uuid4())
        d = tutor_tools.diagnose_step(problem, case["attempt"], trace_id=trace_id)
        h = tutor_tools.generate_hint(problem, case["hint_level"], d.stuck_point,
                                       student_attempt=case["attempt"], trace_id=trace_id)
        correct = any(kw in h.hint_text for kw in case["expect_any"])
        results.append(correct)
        langfuse.score(trace_id=trace_id, name="hint_quality",
                        value=correct, data_type="BOOLEAN",
                        comment=f"problem={case['problem_id']} attempt={case['attempt']!r} "
                                f"stuck_point={d.stuck_point!r} hint={h.hint_text!r} "
                                f"expect_any={case['expect_any']}")
        print(f"[hint] {'OK ' if correct else 'FAIL'} {case['problem_id']} {case['attempt']!r} "
              f"-> {h.hint_text!r}")
    return results


def _pct(results: list[bool]) -> str:
    if not results:
        return "N/A"
    return f"{sum(results)}/{len(results)} ({100 * sum(results) / len(results):.0f}%)"


def main():
    print("=== 의도분류 (우회 탐지율) ===")
    intent_results = eval_intent()
    print("\n=== 오답 진단 정확도 ===")
    diagnosis_results = eval_diagnosis()
    print("\n=== 힌트 품질(진단 반영 여부) ===")
    hint_results = eval_hint()

    print("\n=== 요약 ===")
    print("의도분류:", _pct(intent_results))
    print("오답진단:", _pct(diagnosis_results))
    print("힌트품질:", _pct(hint_results))

    langfuse.flush()   # 프로세스 종료 전 대기 중인 score/trace를 서버로 전송
    print("\nLangfuse에 score 전송 완료.")


if __name__ == "__main__":
    main()
