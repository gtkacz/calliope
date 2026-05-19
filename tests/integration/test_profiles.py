from calliope.domain.enums import ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import ProfileCreate
from calliope.repositories.profiles import ProfileRepository
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
        assert exc.message == "Connection profile does not support the requested capability."
        assert exc.status_code == 400
        assert exc.details == {"name": "local-chat", "capability": "embeddings"}
    else:
        raise AssertionError("expected AppError")


def test_profile_repository_get_by_name_raises_for_missing_profile(db_session) -> None:
    repo = ProfileRepository(db_session)

    try:
        repo.get_by_name("missing-profile")
    except AppError as exc:
        assert exc.code == "connection_profile_not_found"
        assert exc.status_code == 404
        assert exc.details == {"name": "missing-profile"}
    else:
        raise AssertionError("expected AppError")


def test_profile_repository_duplicate_name_raises_and_rolls_back(db_session) -> None:
    repo = ProfileRepository(db_session)
    payload = ProfileCreate(
        name="local-chat",
        kind=ProfileKind.OPENAI_COMPATIBLE,
        base_url="http://localhost:4000/v1",
        model="local-model",
        capabilities=[ProfileCapability.CHAT],
    )
    repo.create(payload)

    try:
        repo.create(payload)
    except AppError as exc:
        assert exc.code == "connection_profile_already_exists"
        assert exc.message == "Connection profile already exists."
        assert exc.status_code == 409
        assert exc.details == {"name": "local-chat"}
    else:
        raise AssertionError("expected AppError")

    assert [profile.name for profile in repo.list()] == ["local-chat"]
