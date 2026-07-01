from pydantic import BaseModel, Field


class TaskProgressRequest(BaseModel):
    reason: str | None = None


class DelayTaskRequest(BaseModel):
    new_deadline: str | None = None
    reason: str | None = None


class MoveTaskRequest(BaseModel):
    target_date: str = Field(min_length=10, max_length=10)
    reason: str | None = None

