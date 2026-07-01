from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    estimated_duration: int | None = None
    deadline: str | None = None
    priority: str | None = None
    tags: list[str] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    estimated_duration: int | None = None
    deadline: str | None = None
    priority: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    estimated_duration: int | None
    deadline: str | None
    priority: str | None
    status: str
    tags: list[str]
    completed_at: datetime | None
