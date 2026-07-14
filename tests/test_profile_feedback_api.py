"""프로필/피드백 API 테스트. Supabase는 fake_supabase 더블로 대체해 네트워크 없이 검증한다."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_profile_create_then_relogin(fake_supabase):
    res1 = client.post("/api/profile", json={
        "name": "지우", "grade": 5, "semester": 1, "password": "1234",
    })
    assert res1.status_code == 200
    user_id = res1.json()["user_id"]

    res2 = client.post("/api/profile", json={
        "name": "지우", "grade": 5, "semester": 1, "password": "1234",
    })
    assert res2.status_code == 200
    assert res2.json()["user_id"] == user_id   # 같은 계정으로 재로그인


def test_profile_wrong_password_returns_409(fake_supabase):
    client.post("/api/profile", json={
        "name": "지우", "grade": 5, "semester": 1, "password": "1234",
    })
    res = client.post("/api/profile", json={
        "name": "지우", "grade": 5, "semester": 1, "password": "다른비번",
    })
    assert res.status_code == 409


def test_profile_create_new_on_conflict_makes_separate_account(fake_supabase):
    res1 = client.post("/api/profile", json={
        "name": "지우", "grade": 5, "semester": 1, "password": "1234",
    })
    res2 = client.post("/api/profile", json={
        "name": "지우", "grade": 6, "semester": 2, "password": "다른비번", "create_new": True,
    })
    assert res2.status_code == 200
    assert res2.json()["user_id"] != res1.json()["user_id"]


def test_feedback_empty_when_no_attempts(fake_supabase):
    profile = client.post("/api/profile", json={
        "name": "서연", "grade": 5, "semester": 1, "password": "1234",
    }).json()

    res = client.get("/api/feedback", params={"user_id": profile["user_id"]})
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["weakest_unit"] is None


def test_feedback_reflects_recorded_attempts_and_grade_filter(fake_supabase):
    from app.repositories import attempt_repo

    profile = client.post("/api/profile", json={
        "name": "하윤", "grade": 5, "semester": 1, "password": "1234",
    }).json()
    user_id = profile["user_id"]

    attempt_repo.record_attempt(user_id, "p1", "분수", hints_used=3, solved=True, grade=4, semester=1)
    attempt_repo.record_attempt(user_id, "p2", "도형", hints_used=0, solved=True, grade=5, semester=1)

    all_res = client.get("/api/feedback", params={"user_id": user_id}).json()
    assert {i["unit"] for i in all_res["items"]} == {"분수", "도형"}
    assert all_res["weakest_unit"] == "분수"

    grade5_res = client.get("/api/feedback", params={"user_id": user_id, "grade": 5}).json()
    assert {i["unit"] for i in grade5_res["items"]} == {"도형"}
