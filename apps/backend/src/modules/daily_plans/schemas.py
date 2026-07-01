from pydantic import BaseModel, Field


class DailyPlanGenerateRequest(BaseModel):
    plan_date: str
    context_window_type: str = "daily_generation"
    trigger_source: str = "manual"


class ScheduleItemResponse(BaseModel):
    id: str
    label: str
    start_time: str
    end_time: str
    status: str
    task_id: str | None


class DailyPlanResponse(BaseModel):
    id: str
    plan_date: str
    status: str
    source: str
    explanation: str | None = None
    items: list[ScheduleItemResponse] = Field(default_factory=list)
