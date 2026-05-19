from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate
from calliope.services.profiles import ProfileService


def test_profile_service_creates_lists_and_requires_capability(db_session) -> None:
    service = ProfileService(db_session)
    created = service.create(
        ProfileCreate(
            name="local-chat",
            kind=ProfileKind.OPENAI_COMPATIBLE,
            base_url="http://localhost:4000/v1",
            model="local-model",
            capabilities=[ProfileCapability.CHAT],
        )
    )

    assert created.name == "local-chat"
    assert service.list()[0].capabilities == [ProfileCapability.CHAT]

    try:
        service.require_capability("local-chat", ProfileCapability.EMBEDDINGS)
    except AppError as exc:
        assert exc.code == "model_profile_missing_capability"
    else:
        raise AssertionError("expected AppError")
