from calliope.config import Settings


def test_settings_defaults_are_local() -> None:
    settings = Settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.api_title == "Calliope"
    assert settings.embedding_dimensions == 384
