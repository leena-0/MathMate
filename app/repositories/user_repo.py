"""학생 프로필 저장소.

이름은 동명이인이 있을 수 있어 유일하지 않다 — 실제 식별자는 (이름, 비밀번호) 조합이다.
비밀번호가 다르면 곧바로 거부하지 않고, "이름이 이미 있음(다른 사람? 오타?)" 상태를
호출부(API)에 알려서 학생이 직접 고르게 한다: 비밀번호 다시 확인 vs 새 계정 생성.
"""
import hashlib
import os
from app.db.supabase_client import get_client

NAME_CONFLICT = "name_conflict"   # 이름은 있는데 비밀번호가 안 맞는 상태를 나타내는 sentinel


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _create(name: str, grade: int, semester: int, password: str) -> dict:
    salt = os.urandom(16).hex()
    created = get_client().table("users").insert({
        "name": name,
        "grade": grade,
        "semester": semester,
        "password_hash": _hash_password(password, salt),
        "password_salt": salt,
    }).execute()
    return created.data[0]


def get_or_create_user(name: str, grade: int, semester: int, password: str,
                        create_new: bool = False) -> dict | str:
    """
    - (이름, 비밀번호)가 일치하는 기존 계정이 있으면 로그인(학년/학기 갱신 후 반환).
    - create_new=True면 일치 여부와 상관없이 새 계정을 만든다(동명이인 확인 후 호출).
    - 이름은 있는데 비밀번호가 안 맞고 create_new=False면 NAME_CONFLICT를 반환한다.
    """
    client = get_client()

    if not create_new:
        existing = client.table("users").select("*").eq("name", name).execute()
        for user in existing.data:
            if _hash_password(password, user["password_salt"]) == user["password_hash"]:
                updates = {}
                if user["grade"] != grade:
                    updates["grade"] = grade
                if user["semester"] != semester:
                    updates["semester"] = semester
                if updates:
                    updated = client.table("users").update(updates).eq("id", user["id"]).execute()
                    return updated.data[0]
                return user
        if existing.data:
            return NAME_CONFLICT

    return _create(name, grade, semester, password)
