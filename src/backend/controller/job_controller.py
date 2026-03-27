"""Controller layer coordinating the sample job workflow routes."""

from typing import Protocol

from src.backend.models.job import JobDetailDTO, ReviewDecision


class InvalidJobIdError(ValueError):
    """Raised when a provided job id is blank after normalization."""


class JobNotFoundError(ValueError):
    """Raised when a requested job does not exist."""


class JobNotResumableError(ValueError):
    """Raised when a job cannot be resumed from its current state."""


class JobNotReviewableError(ValueError):
    """Raised when a job cannot accept a review decision."""


def _normalize_job_id(job_id: str) -> str:
    normalized_job_id = job_id.strip()
    if not normalized_job_id:
        raise InvalidJobIdError("job_id must not be empty")
    return normalized_job_id


def _can_resume(job: JobDetailDTO) -> bool:
    return job.can_resume and job.status in {"paused", "in_progress"}


def _can_review(job: JobDetailDTO) -> bool:
    return job.status == "paused" and job.current_state == "awaiting_review"


class JobGatewayContract(Protocol):
    """Gateway contract used by job controller orchestration."""

    async def get_job(self, job_id: str) -> JobDetailDTO | None: ...

    async def save_job(self, job: JobDetailDTO) -> JobDetailDTO: ...


class InMemoryJobGateway:
    """Small in-memory gateway used by the sample job workflow routes."""

    def __init__(self, jobs: dict[str, JobDetailDTO]) -> None:
        self._jobs = {
            job_id: job.model_copy(deep=True)
            for job_id, job in jobs.items()
        }

    async def get_job(self, job_id: str) -> JobDetailDTO | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return job.model_copy(deep=True)

    async def save_job(self, job: JobDetailDTO) -> JobDetailDTO:
        self._jobs[job.job_id] = job.model_copy(deep=True)
        return self._jobs[job.job_id].model_copy(deep=True)


def _default_jobs() -> dict[str, JobDetailDTO]:
    return {
        "job-review-321": JobDetailDTO(
            job_id="job-review-321",
            workflow_type="pm_tool_workflow",
            current_state="awaiting_review",
            status="paused",
            state_version=6,
            resume_count=1,
            can_resume=False,
            last_error="Pending PM review",
        ),
        "job-paused-123": JobDetailDTO(
            job_id="job-paused-123",
            workflow_type="pm_tool_workflow",
            current_state="awaiting_requirements",
            status="paused",
            state_version=3,
            resume_count=0,
            can_resume=True,
            last_error="Waiting for product requirements",
        ),
        "job-running-456": JobDetailDTO(
            job_id="job-running-456",
            workflow_type="pm_tool_workflow",
            current_state="drafting_pr",
            status="in_progress",
            state_version=5,
            resume_count=1,
            can_resume=True,
        ),
        "job-completed-789": JobDetailDTO(
            job_id="job-completed-789",
            workflow_type="pm_tool_workflow",
            current_state="published_summary",
            status="completed",
            state_version=8,
            resume_count=0,
            can_resume=False,
        ),
    }


class JobController:
    """Application workflow service for the sample job routes."""

    def __init__(self, gateway: JobGatewayContract) -> None:
        self._gateway = gateway

    async def get_job_detail(self, job_id: str) -> JobDetailDTO:
        normalized_job_id = _normalize_job_id(job_id)
        job = await self._gateway.get_job(normalized_job_id)
        if job is None:
            raise JobNotFoundError("job not found")
        return job

    async def resume_job(self, job_id: str) -> JobDetailDTO:
        job = await self.get_job_detail(job_id)
        if not _can_resume(job):
            raise JobNotResumableError(
                f"job is not resumable from state '{job.current_state}' and status '{job.status}'"
            )

        resumed_job = job.model_copy(
            update={
                "current_state": (
                    "drafting_pr"
                    if job.status == "paused"
                    else job.current_state
                ),
                "status": "in_progress",
                "state_version": job.state_version + 1,
                "resume_count": job.resume_count + 1,
                "can_resume": True,
                "last_error": None,
            }
        )
        return await self._gateway.save_job(resumed_job)

    async def review_job(
        self,
        job_id: str,
        decision: ReviewDecision,
    ) -> JobDetailDTO:
        job = await self.get_job_detail(job_id)
        if not _can_review(job):
            raise JobNotReviewableError(
                f"job is not reviewable from state '{job.current_state}' and status '{job.status}'"
            )

        updated_fields: dict[str, object] = {
            "state_version": job.state_version + 1,
            "last_error": None,
        }
        if decision == "approve":
            updated_fields.update(
                {
                    "current_state": "published_summary",
                    "status": "completed",
                    "can_resume": False,
                }
            )
        else:
            updated_fields.update(
                {
                    "current_state": "changes_requested",
                    "status": "paused",
                    "can_resume": True,
                    "last_error": "Changes requested in review",
                }
            )

        reviewed_job = job.model_copy(update=updated_fields)
        return await self._gateway.save_job(reviewed_job)


def build_job_controller() -> JobController:
    """Build the sample controller used by mounted job handlers."""
    return JobController(InMemoryJobGateway(_default_jobs()))


__all__ = [
    "InMemoryJobGateway",
    "InvalidJobIdError",
    "JobController",
    "JobGatewayContract",
    "JobNotFoundError",
    "JobNotResumableError",
    "JobNotReviewableError",
    "build_job_controller",
]
