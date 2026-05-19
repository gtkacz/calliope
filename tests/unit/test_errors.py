from datetime import UTC, datetime

from fastapi.testclient import TestClient

from calliope.api.app import create_app
from calliope.domain.errors import AppError


def test_app_error_maps_to_stable_json() -> None:
    app = create_app()

    @app.get("/raise-test-error")
    def raise_error() -> None:
        raise AppError(
            code="workspace_not_found",
            message="Workspace not found.",
            status_code=404,
            details={"workspace_id": "workspace_123"},
        )

    response = TestClient(app).get("/raise-test-error")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "workspace_not_found",
            "message": "Workspace not found.",
            "details": {"workspace_id": "workspace_123"},
        }
    }


def test_app_error_details_are_json_encoded() -> None:
    app = create_app()

    @app.get("/raise-datetime-detail")
    def raise_error() -> None:
        raise AppError(
            code="workspace_unavailable",
            message="Workspace unavailable.",
            status_code=503,
            details={"when": datetime(2026, 5, 19, tzinfo=UTC)},
        )

    response = TestClient(app).get("/raise-datetime-detail")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "workspace_unavailable",
            "message": "Workspace unavailable.",
            "details": {"when": "2026-05-19T00:00:00+00:00"},
        }
    }


def test_app_error_string_uses_message() -> None:
    error = AppError(
        code="workspace_not_found",
        message="Workspace not found.",
        status_code=404,
    )

    assert str(error) == "Workspace not found."
