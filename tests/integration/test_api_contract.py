from typing import Any

from fastapi.testclient import TestClient

from calliope.api.app import create_app
from calliope.config import Settings

SETTINGS_WITHOUT_ENV_FILE: dict[str, Any] = {"_env_file": None}


def test_openapi_document_exists() -> None:
    client = TestClient(create_app(Settings(api_title="Calliope", **SETTINGS_WITHOUT_ENV_FILE)))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "Calliope"


def test_app_retains_injected_settings() -> None:
    settings = Settings(api_title="Calliope Test", **SETTINGS_WITHOUT_ENV_FILE)
    app = create_app(settings)

    assert app.state.settings is settings
