from typing import Annotated, Any

from calliope.api.dependencies import get_db_session
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate, ProfileRead
from calliope.services.profiles import ProfileService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1/profiles")


@router.post("", response_model=ProfileRead)
def create_profile(
    payload: ProfileCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> ProfileRead:
    return ProfileService(session).create(payload)


@router.get("", response_model=list[ProfileRead])
def list_profiles(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[ProfileRead]:
    return ProfileService(session).list()


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(
    profile_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> ProfileRead:
    for profile in ProfileService(session).list():
        if profile.id == profile_id:
            return profile

    raise AppError(
        code="connection_profile_not_found",
        message="Connection profile not found.",
        status_code=404,
        details={"profile_id": profile_id},
    )


@router.post("/{profile_id}/test")
def test_profile(
    profile_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    profile = get_profile(profile_id, session)
    return {
        "ok": True,
        "id": profile.id,
        "capabilities": [value.value for value in profile.capabilities],
    }
