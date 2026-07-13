"""학생 프로필 스키마. 비밀번호는 같은 이름을 다른 사람이 쓰는 것만 막는 용도(자동 로그인 아님)."""
from pydantic import BaseModel


class ProfileRequest(BaseModel):
    name: str
    grade: int
    semester: int
    password: str
    create_new: bool = False   # True면 이름이 겹쳐도 동명이인으로 보고 새 계정 생성


class ProfileResponse(BaseModel):
    user_id: int
    name: str
    grade: int
    semester: int
