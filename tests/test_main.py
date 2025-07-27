from fastapi.testclient import TestClient
from src.backend.web.rest.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI AI API integration"}


def test_chat_endpoint_exists():
    response = client.get("/chat")
    # This will return 405 Method Not Allowed because it's a POST endpoint
    assert response.status_code == 405
