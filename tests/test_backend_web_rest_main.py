from fastapi.testclient import TestClient

from src.backend.web.rest.main import app, read_root


def test_read_root_returns_welcome_message():
    assert read_root() == {"message": "Welcome to the FastAPI template"}


def test_root_endpoint_returns_welcome_message():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI template"}
