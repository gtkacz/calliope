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
