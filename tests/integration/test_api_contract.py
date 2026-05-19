from fastapi.testclient import TestClient

from calliope.api.app import create_app


def test_openapi_document_exists() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "Calliope"
