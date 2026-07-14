"""학생 프로필(회원가입 대체) API. 이름은 동명이인이 있을 수 있어 (이름, 비밀번호) 조합으로 식별한다."""
from fastapi import APIRouter, HTTPException
from app.repositories import user_repo
from app.schemas.profile import ProfileRequest, ProfileResponse

router = APIRouter()


@router.post("/profile", response_model=ProfileResponse)
def create_or_get_profile(req: ProfileRequest):
    result = user_repo.get_or_create_user(req.name, req.grade, req.semester, req.password, req.create_new)
    if result == user_repo.NAME_CONFLICT:
        # 409: 이름은 있는데 비밀번호가 안 맞음 — 오타인지 동명이인인지는 학생이 선택
        raise HTTPException(status_code=409, detail="이미 있는 이름인데 비밀번호가 달라요.")
    return ProfileResponse(user_id=result["id"], name=result["name"], grade=result["grade"],
                            semester=result["semester"])
