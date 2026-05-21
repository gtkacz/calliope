from calliope.domain.enums import ProfileCapability
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate, ProfilePatch, ProfileRead
from calliope.repositories.profiles import ProfileRepository
from sqlalchemy.orm import Session


class ProfileService:
    def __init__(self, session: Session) -> None:
        self.repository = ProfileRepository(session)

    def create(self, payload: ProfileCreate) -> ProfileRead:
        return self.repository.create(payload)

    def list(self) -> list[ProfileRead]:
        return self.repository.list()

    def get_by_name(self, name: str) -> ProfileRead:
        return self.repository.get_by_name(name)

    def get_by_id(self, profile_id: str) -> ProfileRead:
        return self.repository.get_by_id(profile_id)

    def update(self, profile_id: str, payload: ProfilePatch) -> ProfileRead:
        return self.repository.update(profile_id, payload)

    def delete(self, profile_id: str) -> None:
        self.repository.delete(profile_id)

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

    def require_capability_by_id(
        self,
        profile_id: str,
        capability: ProfileCapability,
    ) -> ProfileRead:
        profile = self.get_by_id(profile_id)
        if capability not in profile.capabilities:
            raise AppError(
                code="model_profile_missing_capability",
                message="Connection profile does not support the requested capability.",
                status_code=400,
                details={
                    "profile_id": profile_id,
                    "capability": capability.value,
                },
            )

        return profile
