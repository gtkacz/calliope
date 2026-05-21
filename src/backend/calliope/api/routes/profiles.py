from typing import Annotated, Any

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import ProfileCreate, ProfilePatch, ProfileRead
from calliope.services.profiles import ProfileService
from fastapi import APIRouter, Depends, Response, status
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
    return ProfileService(session).get_by_id(profile_id)


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(
    profile_id: str,
    payload: ProfilePatch,
    session: Annotated[Session, Depends(get_db_session)],
) -> ProfileRead:
    return ProfileService(session).update(profile_id, payload)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    ProfileService(session).delete(profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
