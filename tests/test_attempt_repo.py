"""진척도(attempt_repo) 테스트. Supabase는 fake_supabase 더블로 대체해 네트워크 없이 검증한다."""
from app.repositories import attempt_repo


def _record(user_id, unit, hints_used, grade=5, semester=1, solved=True, problem_id=None):
    attempt_repo.record_attempt(
        user_id=user_id,
        problem_id=problem_id or f"{unit}-{hints_used}-{grade}-{semester}",
        unit=unit,
        hints_used=hints_used,
        solved=solved,
        grade=grade,
        semester=semester,
    )


def test_only_solved_attempts_are_counted(fake_supabase):
    _record(1, "도형", 1, solved=True, problem_id="p1")
    _record(1, "도형", 3, solved=False, problem_id="p2")   # 못 풀었으면 집계에서 빠져야 함

    items = attempt_repo.get_unit_mastery(1)
    assert len(items) == 1
    assert items[0]["problems_attempted"] == 1
    assert items[0]["avg_hints_used"] == 1.0


def test_mastery_level_thresholds(fake_supabase):
    _record(1, "잘함단원", 0, problem_id="a")
    _record(1, "보통단원", 1, problem_id="b")
    _record(1, "취약단원", 2, problem_id="c")

    by_unit = {i["unit"]: i for i in attempt_repo.get_unit_mastery(1)}
    assert by_unit["잘함단원"]["mastery_level"] == "잘함"
    assert by_unit["보통단원"]["mastery_level"] == "보통"
    assert by_unit["취약단원"]["mastery_level"] == "취약"


def test_grade_semester_filter_narrows_results(fake_supabase):
    _record(1, "분수", 3, grade=4, semester=1, problem_id="a")
    _record(1, "도형", 1, grade=5, semester=1, problem_id="b")

    all_items = attempt_repo.get_unit_mastery(1)
    assert {i["unit"] for i in all_items} == {"분수", "도형"}

    grade5_items = attempt_repo.get_unit_mastery(1, grade=5)
    assert {i["unit"] for i in grade5_items} == {"도형"}

    grade4_items = attempt_repo.get_unit_mastery(1, grade=4, semester=1)
    assert {i["unit"] for i in grade4_items} == {"분수"}


def test_weakest_prefers_more_hints_first(fake_supabase):
    _record(1, "많이틀림", 3, problem_id="a")
    _record(1, "적게틀림", 1, problem_id="b")

    items = attempt_repo.get_unit_mastery(1)
    assert items[0]["unit"] == "많이틀림"   # 평균 힌트가 더 높은 쪽이 먼저(더 약함)


def test_weakest_tiebreak_prefers_fewer_attempts(fake_supabase):
    """평균 힌트가 정확히 같으면(반올림 우연이 아니라 진짜 동점), 문제를 적게 푼(연습이 덜 된) 쪽을 더 약하다고 본다."""
    for i in range(6):
        _record(1, "많이푼단원", 1, problem_id=f"many-{i}")
    _record(1, "한번푼단원", 1, problem_id="once")

    items = attempt_repo.get_unit_mastery(1)
    assert items[0]["unit"] == "한번푼단원"
    assert items[0]["problems_attempted"] == 1
    assert items[1]["unit"] == "많이푼단원"
    assert items[1]["problems_attempted"] == 6


def test_no_attempts_returns_empty_list(fake_supabase):
    assert attempt_repo.get_unit_mastery(999) == []
