from sqlalchemy import select
from sqlalchemy.orm import Session

from calliope.db.models import ConnectionProfile
from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.schemas import ProfileCreate, ProfileRead


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
        self.session.commit()
        self.session.refresh(profile)

        return self._to_read(profile)

    def list(self) -> list[ProfileRead]:
        profiles = self.session.scalars(
            select(ConnectionProfile).order_by(ConnectionProfile.created_at, ConnectionProfile.id)
        ).all()

        return [self._to_read(profile) for profile in profiles]

    def get_by_name(self, name: str) -> ProfileRead | None:
        profile = self.session.scalar(
            select(ConnectionProfile).where(ConnectionProfile.name == name)
        )
        if profile is None:
            return None

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
