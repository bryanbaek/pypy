"""Tests for mounted job detail and resume routes."""

from fastapi.testclient import TestClient

from src.backend.main import create_app
from src.backend.models.job import YOLO_MARKER


def test_job_detail_route_returns_expected_payload() -> None:
    response = TestClient(create_app()).get("/jobs/job-paused-123/detail")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-paused-123",
        "workflow_type": "pm_tool_workflow",
        "current_state": "awaiting_requirements",
        "status": "paused",
        "state_version": 3,
        "resume_count": 0,
        "can_resume": True,
        "last_error": "Waiting for product requirements",
        "ticket_marker": None,
        "pull_request_labels": [],
    }


def test_resume_route_returns_updated_job_state() -> None:
    client = TestClient(create_app())

    response = client.post("/jobs/job-paused-123/resume")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "job": {
            "job_id": "job-paused-123",
            "workflow_type": "pm_tool_workflow",
            "current_state": "drafting_pr",
            "status": "in_progress",
            "state_version": 4,
            "resume_count": 1,
            "can_resume": True,
            "last_error": None,
            "ticket_marker": None,
            "pull_request_labels": [],
        },
    }
    assert client.get("/jobs/job-paused-123/detail").json() == {
        "job_id": "job-paused-123",
        "workflow_type": "pm_tool_workflow",
        "current_state": "drafting_pr",
        "status": "in_progress",
        "state_version": 4,
        "resume_count": 1,
        "can_resume": True,
        "last_error": None,
        "ticket_marker": None,
        "pull_request_labels": [],
    }


def test_yolo_resume_route_propagates_pull_request_label() -> None:
    client = TestClient(create_app())

    response = client.post("/jobs/job-yolo-321/resume")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "job": {
            "job_id": "job-yolo-321",
            "workflow_type": "pm_tool_workflow",
            "current_state": "drafting_pr",
            "status": "in_progress",
            "state_version": 3,
            "resume_count": 1,
            "can_resume": True,
            "last_error": None,
            "ticket_marker": YOLO_MARKER,
            "pull_request_labels": [YOLO_MARKER],
        },
    }
    assert client.get("/jobs/job-yolo-321/detail").json() == {
        "job_id": "job-yolo-321",
        "workflow_type": "pm_tool_workflow",
        "current_state": "drafting_pr",
        "status": "in_progress",
        "state_version": 3,
        "resume_count": 1,
        "can_resume": True,
        "last_error": None,
        "ticket_marker": YOLO_MARKER,
        "pull_request_labels": [YOLO_MARKER],
    }


def test_job_detail_route_rejects_invalid_job_ids() -> None:
    response = TestClient(create_app()).get("/jobs/%20%20/detail")

    assert response.status_code == 400
    assert response.json() == {"detail": "job_id must not be empty"}


def test_job_detail_route_returns_not_found_for_unknown_jobs() -> None:
    response = TestClient(create_app()).get("/jobs/job-missing-000/detail")

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_resume_route_returns_conflict_for_non_resumable_jobs() -> None:
    response = TestClient(create_app()).post("/jobs/job-completed-789/resume")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "job is not resumable from status 'completed'"
    }
