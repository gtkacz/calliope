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
        profile = self.repository.get_by_name(name)
        if profile is None:
            raise AppError(
                code="connection_profile_not_found",
                message="Connection profile not found.",
                status_code=404,
                details={"name": name},
            )

        return profile

    def require_capability(self, name: str, capability: ProfileCapability) -> ProfileRead:
        profile = self.get_by_name(name)
        if capability not in profile.capabilities:
            raise AppError(
                code="model_profile_missing_capability",
                message="Model profile is missing required capability.",
                details={
                    "name": name,
                    "required_capability": capability.value,
                    "capabilities": [
                        profile_capability.value for profile_capability in profile.capabilities
                    ],
                },
            )

        return profile
