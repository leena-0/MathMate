"""프로필(user_repo) 테스트. Supabase는 fake_supabase 더블로 대체해 네트워크 없이 검증한다."""
from app.repositories import user_repo


def test_creates_new_user(fake_supabase):
    user = user_repo.get_or_create_user("민준", 5, 1, "1234")
    assert user["name"] == "민준"
    assert user["grade"] == 5
    assert user["semester"] == 1
    assert "id" in user


def test_relogin_with_correct_password_returns_same_user(fake_supabase):
    created = user_repo.get_or_create_user("민준", 5, 1, "1234")
    again = user_repo.get_or_create_user("민준", 5, 1, "1234")
    assert again["id"] == created["id"]
    assert len(fake_supabase._tables["users"].rows) == 1   # 중복 생성 안 됨


def test_relogin_updates_grade_and_semester(fake_supabase):
    created = user_repo.get_or_create_user("민준", 5, 1, "1234")
    updated = user_repo.get_or_create_user("민준", 6, 2, "1234")
    assert updated["id"] == created["id"]        # 같은 계정 유지
    assert updated["grade"] == 6
    assert updated["semester"] == 2


def test_wrong_password_returns_conflict_not_error(fake_supabase):
    user_repo.get_or_create_user("민준", 5, 1, "1234")
    result = user_repo.get_or_create_user("민준", 5, 1, "다른비번")
    assert result == user_repo.NAME_CONFLICT


def test_create_new_explicit_makes_separate_account_for_homonym(fake_supabase):
    first = user_repo.get_or_create_user("민준", 5, 1, "1234")
    second = user_repo.get_or_create_user("민준", 6, 2, "다른비번", create_new=True)
    assert second["id"] != first["id"]           # 동명이인 = 별도 계정
    assert len(fake_supabase._tables["users"].rows) == 2

    # 원래 계정은 그대로 로그인 가능해야 한다.
    relogin = user_repo.get_or_create_user("민준", 5, 1, "1234")
    assert relogin["id"] == first["id"]
