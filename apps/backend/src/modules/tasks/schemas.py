from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    estimated_duration: int | None = None
    deadline: str | None = None
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    task_type: str = Field(default="scheduled", pattern=r"^(scheduled|flexible)$")
    priority: str | None = None
    tags: list[str] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    estimated_duration: int | None = None
    deadline: str | None = None
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    task_type: str | None = Field(default=None, pattern=r"^(scheduled|flexible)$")
    priority: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    estimated_duration: int | None
    deadline: str | None
    start_time: str | None
    task_type: str
    priority: str | None
    status: str
    tags: list[str]
    completed_at: datetime | None


class HistoryDayInfo(BaseModel):
    date: str
    total: int
    completed: int
    pending: int
    tasks: list[TaskResponse]


class HistoryResponse(BaseModel):
    days: list[HistoryDayInfo]
    from_date: str
    to_date: str
    total_tasks: int
    total_completed: int
    total_pending: int
