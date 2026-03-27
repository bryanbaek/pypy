"""Tests for mounted job list, detail, resume, and review routes."""

from fastapi.testclient import TestClient

from src.backend.main import create_app


def test_job_list_route_returns_dashboard_items() -> None:
    response = TestClient(create_app()).get("/jobs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "job_id": "job-paused-123",
            "workflow_type": "pm_tool_workflow",
            "current_state": "awaiting_requirements",
            "status": "paused",
            "state_version": 3,
            "resume_count": 0,
            "can_resume": True,
            "approval_status": "pending",
            "can_approve": True,
            "can_reject": True,
            "last_error": "Waiting for product requirements",
        },
        {
            "job_id": "job-running-456",
            "workflow_type": "pm_tool_workflow",
            "current_state": "drafting_pr",
            "status": "in_progress",
            "state_version": 5,
            "resume_count": 1,
            "can_resume": True,
            "approval_status": "approved",
            "can_approve": False,
            "can_reject": False,
            "last_error": None,
        },
        {
            "job_id": "job-completed-789",
            "workflow_type": "pm_tool_workflow",
            "current_state": "published_summary",
            "status": "completed",
            "state_version": 8,
            "resume_count": 0,
            "can_resume": False,
            "approval_status": "approved",
            "can_approve": False,
            "can_reject": False,
            "last_error": None,
        },
    ]


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
        "approval_status": "pending",
        "can_approve": True,
        "can_reject": True,
        "last_error": "Waiting for product requirements",
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
            "approval_status": "approved",
            "can_approve": False,
            "can_reject": False,
            "last_error": None,
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
        "approval_status": "approved",
        "can_approve": False,
        "can_reject": False,
        "last_error": None,
    }


def test_review_route_approves_pending_job() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/jobs/job-paused-123/review",
        json={"decision": "approve"},
    )

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
            "approval_status": "approved",
            "can_approve": False,
            "can_reject": False,
            "last_error": None,
        },
    }
    assert client.get("/jobs/job-paused-123/detail").json()["approval_status"] == "approved"


def test_review_route_rejects_pending_job() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/jobs/job-paused-123/review",
        json={"decision": "reject"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "job": {
            "job_id": "job-paused-123",
            "workflow_type": "pm_tool_workflow",
            "current_state": "requirements_rejected",
            "status": "failed",
            "state_version": 4,
            "resume_count": 0,
            "can_resume": False,
            "approval_status": "rejected",
            "can_approve": False,
            "can_reject": False,
            "last_error": "Requirements were rejected",
        },
    }
    assert client.get("/jobs/job-paused-123/detail").json()["status"] == "failed"


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


def test_review_route_returns_conflict_for_stale_dashboard_actions() -> None:
    client = TestClient(create_app())

    first_response = client.post(
        "/jobs/job-paused-123/review",
        json={"decision": "approve"},
    )
    stale_response = client.post(
        "/jobs/job-paused-123/review",
        json={"decision": "reject"},
    )

    assert first_response.status_code == 200
    assert stale_response.status_code == 409
    assert stale_response.json() == {"detail": "job is not awaiting approval"}
    assert client.get("/jobs/job-paused-123/detail").json() == {
        "job_id": "job-paused-123",
        "workflow_type": "pm_tool_workflow",
        "current_state": "drafting_pr",
        "status": "in_progress",
        "state_version": 4,
        "resume_count": 1,
        "can_resume": True,
        "approval_status": "approved",
        "can_approve": False,
        "can_reject": False,
        "last_error": None,
    }
