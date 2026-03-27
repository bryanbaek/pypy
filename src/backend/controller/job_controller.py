"""Controller layer coordinating the sample job workflow routes."""

from typing import Protocol

from src.backend.models.job import JobDetailDTO, JobReviewDecision


class InvalidJobIdError(ValueError):
    """Raised when a provided job id is blank after normalization."""


class JobNotFoundError(ValueError):
    """Raised when a requested job does not exist."""


class JobNotResumableError(ValueError):
    """Raised when a job cannot be resumed from its current state."""


class JobNotReviewableError(ValueError):
    """Raised when a job cannot be approved or rejected."""


def _normalize_job_id(job_id: str) -> str:
    normalized_job_id = job_id.strip()
    if not normalized_job_id:
        raise InvalidJobIdError("job_id must not be empty")
    return normalized_job_id


def _can_resume(status: str) -> bool:
    return status in {"paused", "in_progress"}


def _can_review(job: JobDetailDTO) -> bool:
    return (
        job.workflow_type == "pm_tool_workflow"
        and job.status == "paused"
        and job.current_state == "awaiting_requirements"
        and job.approval_status == "pending"
    )


def _sync_review_capabilities(job: JobDetailDTO) -> JobDetailDTO:
    can_review = _can_review(job)
    return job.model_copy(
        update={
            "can_approve": can_review,
            "can_reject": can_review,
        }
    )


def _build_approved_job(job: JobDetailDTO) -> JobDetailDTO:
    return job.model_copy(
        update={
            "current_state": "drafting_pr",
            "status": "in_progress",
            "state_version": job.state_version + 1,
            "resume_count": job.resume_count + 1,
            "can_resume": True,
            "approval_status": "approved",
            "last_error": None,
        }
    )


def _build_rejected_job(job: JobDetailDTO) -> JobDetailDTO:
    return job.model_copy(
        update={
            "current_state": "requirements_rejected",
            "status": "failed",
            "state_version": job.state_version + 1,
            "can_resume": False,
            "approval_status": "rejected",
            "last_error": "Requirements were rejected",
        }
    )


class JobGatewayContract(Protocol):
    """Gateway contract used by job controller orchestration."""

    async def list_jobs(self) -> list[JobDetailDTO]: ...

    async def get_job(self, job_id: str) -> JobDetailDTO | None: ...

    async def save_job(self, job: JobDetailDTO) -> JobDetailDTO: ...


class InMemoryJobGateway:
    """Small in-memory gateway used by the sample job workflow routes."""

    def __init__(self, jobs: dict[str, JobDetailDTO]) -> None:
        self._jobs = {
            job_id: job.model_copy(deep=True)
            for job_id, job in jobs.items()
        }

    async def list_jobs(self) -> list[JobDetailDTO]:
        return [job.model_copy(deep=True) for job in self._jobs.values()]

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
        "job-paused-123": JobDetailDTO(
            job_id="job-paused-123",
            workflow_type="pm_tool_workflow",
            current_state="awaiting_requirements",
            status="paused",
            state_version=3,
            resume_count=0,
            can_resume=True,
            approval_status="pending",
            can_approve=True,
            can_reject=True,
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
            approval_status="approved",
        ),
        "job-completed-789": JobDetailDTO(
            job_id="job-completed-789",
            workflow_type="pm_tool_workflow",
            current_state="published_summary",
            status="completed",
            state_version=8,
            resume_count=0,
            can_resume=False,
            approval_status="approved",
        ),
    }


class JobController:
    """Application workflow service for the sample job routes."""

    def __init__(self, gateway: JobGatewayContract) -> None:
        self._gateway = gateway

    async def list_jobs(self) -> list[JobDetailDTO]:
        jobs = await self._gateway.list_jobs()
        return [_sync_review_capabilities(job) for job in jobs]

    async def get_job_detail(self, job_id: str) -> JobDetailDTO:
        normalized_job_id = _normalize_job_id(job_id)
        job = await self._gateway.get_job(normalized_job_id)
        if job is None:
            raise JobNotFoundError("job not found")
        return _sync_review_capabilities(job)

    async def _save_job(self, job: JobDetailDTO) -> JobDetailDTO:
        saved_job = await self._gateway.save_job(_sync_review_capabilities(job))
        return _sync_review_capabilities(saved_job)

    async def resume_job(self, job_id: str) -> JobDetailDTO:
        job = await self.get_job_detail(job_id)
        if not _can_resume(job.status):
            raise JobNotResumableError(
                f"job is not resumable from status '{job.status}'"
            )

        resumed_job = (
            _build_approved_job(job)
            if job.status == "paused" and job.current_state == "awaiting_requirements"
            else job.model_copy(
                update={
                    "status": "in_progress",
                    "state_version": job.state_version + 1,
                    "resume_count": job.resume_count + 1,
                    "can_resume": True,
                    "last_error": None,
                }
            )
        )
        return await self._save_job(resumed_job)

    async def review_job(
        self,
        job_id: str,
        decision: JobReviewDecision,
    ) -> JobDetailDTO:
        job = await self.get_job_detail(job_id)
        if not _can_review(job):
            raise JobNotReviewableError("job is not awaiting approval")

        reviewed_job = (
            _build_approved_job(job)
            if decision == "approve"
            else _build_rejected_job(job)
        )
        return await self._save_job(reviewed_job)


def build_job_controller() -> JobController:
    """Build the sample controller used by mounted job handlers."""
    return JobController(InMemoryJobGateway(_default_jobs()))


__all__ = [
    "InMemoryJobGateway",
    "InvalidJobIdError",
    "JobController",
    "JobGatewayContract",
    "JobNotFoundError",
    "JobNotReviewableError",
    "JobNotResumableError",
    "build_job_controller",
]
