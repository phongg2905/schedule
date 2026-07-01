from pydantic import BaseModel, Field


class InsightResponse(BaseModel):
    summary_date: str
    total_tasks: int
    completed_tasks: int
    skipped_tasks: int
    deferred_tasks: int
    pending_tasks: int
    top_focus: str = Field(default="")
    highlights: list[str] = Field(default_factory=list)

