"""DTOs for the sample job workflow routes."""

from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["paused", "in_progress", "completed", "failed"]
JobApprovalStatus = Literal["pending", "approved", "rejected"]
JobReviewDecision = Literal["approve", "reject"]


class JobDetailDTO(BaseModel):
    """Serializable job detail payload for workflow-oriented handlers."""

    job_id: str
    workflow_type: str
    current_state: str
    status: JobStatus
    state_version: int = Field(ge=1)
    resume_count: int = Field(default=0, ge=0)
    can_resume: bool
    approval_status: JobApprovalStatus = "pending"
    can_approve: bool = False
    can_reject: bool = False
    last_error: str | None = None


class ResumeJobResponseDTO(BaseModel):
    """Response payload returned after a successful job resume action."""

    status: Literal["ok"] = "ok"
    job: JobDetailDTO


class ReviewJobRequestDTO(BaseModel):
    """Request payload for approve/reject workflow decisions."""

    decision: JobReviewDecision


class ReviewJobResponseDTO(BaseModel):
    """Response payload returned after a successful workflow review action."""

    status: Literal["ok"] = "ok"
    job: JobDetailDTO


__all__ = [
    "JobApprovalStatus",
    "JobDetailDTO",
    "JobReviewDecision",
    "JobStatus",
    "ResumeJobResponseDTO",
    "ReviewJobRequestDTO",
    "ReviewJobResponseDTO",
]
