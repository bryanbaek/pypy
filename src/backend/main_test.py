"""Tests for the FastAPI application entrypoint."""

from fastapi.testclient import TestClient

from src.backend.main import app, create_app


def test_create_app_registers_expected_routes() -> None:
    route_paths = {route.path for route in create_app().routes}

    assert "/" in route_paths
    assert "/health" in route_paths


def test_root_endpoint_returns_template_message() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI template"}


def test_health_endpoint_returns_ok_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
