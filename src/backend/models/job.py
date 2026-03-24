"""DTOs for the sample job workflow routes."""

from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["paused", "in_progress", "completed", "failed"]
YoloMarker = Literal["berry:yolo"]
YOLO_MARKER = "berry:yolo"


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
    ticket_marker: YoloMarker | None = None
    pull_request_labels: list[str] = Field(default_factory=list)


class ResumeJobResponseDTO(BaseModel):
    """Response payload returned after a successful job resume action."""

    status: Literal["ok"] = "ok"
    job: JobDetailDTO


__all__ = [
    "JobDetailDTO",
    "JobStatus",
    "ResumeJobResponseDTO",
    "YOLO_MARKER",
    "YoloMarker",
]
