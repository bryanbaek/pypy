"""DTOs for the sample job workflow routes."""

from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["paused", "in_progress", "completed", "failed"]
ReviewDecision = Literal["approve", "reject"]


class JobDetailDTO(BaseModel):
    """Serializable job detail payload for workflow-oriented handlers."""

    job_id: str
    workflow_type: str
    current_state: str
    status: JobStatus
    state_version: int = Field(ge=1)
    resume_count: int = Field(default=0, ge=0)
    can_resume: bool
    last_error: str | None = None


class ResumeJobResponseDTO(BaseModel):
    """Response payload returned after a successful job resume action."""

    status: Literal["ok"] = "ok"
    job: JobDetailDTO


class ReviewJobRequestDTO(BaseModel):
    """Request payload for a review decision submitted from any client."""

    decision: ReviewDecision


class ReviewJobResponseDTO(BaseModel):
    """Response payload returned after a successful review decision."""

    status: Literal["ok"] = "ok"
    job: JobDetailDTO


__all__ = [
    "JobDetailDTO",
    "JobStatus",
    "ResumeJobResponseDTO",
    "ReviewDecision",
    "ReviewJobRequestDTO",
    "ReviewJobResponseDTO",
]
