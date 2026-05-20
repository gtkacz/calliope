from calliope.db.models import ConnectionProfile
from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate, ProfileRead
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: ProfileCreate) -> ProfileRead:
        profile = ConnectionProfile(
            name=payload.name,
            kind=payload.kind.value,
            base_url=payload.base_url,
            model=payload.model,
            api_key_ref=payload.api_key_ref,
            capabilities_json=[capability.value for capability in payload.capabilities],
        )
        self.session.add(profile)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                code="connection_profile_already_exists",
                message="Connection profile already exists.",
                status_code=409,
                details={"name": payload.name},
            ) from exc
        self.session.refresh(profile)

        return self._to_read(profile)

    def list(self) -> list[ProfileRead]:
        profiles = self.session.scalars(
            select(ConnectionProfile).order_by(ConnectionProfile.created_at, ConnectionProfile.id)
        ).all()

        return [self._to_read(profile) for profile in profiles]

    def get_by_name(self, name: str) -> ProfileRead:
        profile = self.session.scalar(
            select(ConnectionProfile).where(ConnectionProfile.name == name)
        )
        if profile is None:
            raise AppError(
                code="connection_profile_not_found",
                message="Connection profile not found.",
                status_code=404,
                details={"name": name},
            )

        return self._to_read(profile)

    def get_by_id(self, profile_id: str) -> ProfileRead:
        profile = self.session.get(ConnectionProfile, profile_id)
        if profile is None:
            raise AppError(
                code="connection_profile_not_found",
                message="Connection profile not found.",
                status_code=404,
                details={"profile_id": profile_id},
            )

        return self._to_read(profile)

    @staticmethod
    def _to_read(profile: ConnectionProfile) -> ProfileRead:
        return ProfileRead(
            id=profile.id,
            name=profile.name,
            kind=ProfileKind(profile.kind),
            base_url=profile.base_url,
            model=profile.model,
            api_key_ref=profile.api_key_ref,
            capabilities=[
                ProfileCapability(capability) for capability in profile.capabilities_json
            ],
            created_at=profile.created_at,
        )
