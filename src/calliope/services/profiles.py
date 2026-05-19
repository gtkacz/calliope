from sqlalchemy.orm import Session

from calliope.domain.enums import ProfileCapability
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate, ProfileRead
from calliope.repositories.profiles import ProfileRepository


class ProfileService:
    def __init__(self, session: Session) -> None:
        self.repository = ProfileRepository(session)

    def create(self, payload: ProfileCreate) -> ProfileRead:
        return self.repository.create(payload)

    def list(self) -> list[ProfileRead]:
        return self.repository.list()

    def get_by_name(self, name: str) -> ProfileRead:
        return self.repository.get_by_name(name)

    def require_capability(self, name: str, capability: ProfileCapability) -> ProfileRead:
        profile = self.get_by_name(name)
        if capability not in profile.capabilities:
            raise AppError(
                code="model_profile_missing_capability",
                message="Connection profile does not support the requested capability.",
                status_code=400,
                details={
                    "name": name,
                    "capability": capability.value,
                },
            )

        return profile
