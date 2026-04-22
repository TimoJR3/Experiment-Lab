"""Basic API tests for the project scaffold."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    """Health endpoint should confirm that the API is running."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
