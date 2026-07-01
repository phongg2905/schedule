from pydantic import BaseModel, Field


class GenerateDailyPlanRequest(BaseModel):
    plan_date: str
    context_window_type: str = "ai_generation"
    trigger_source: str = "manual"


class ExplainDailyPlanRequest(BaseModel):
    daily_plan_id: str
    question: str = Field(default="Why is this the plan?")


class AdjustDailyPlanRequest(BaseModel):
    daily_plan_id: str
    change_description: str = Field(min_length=1, max_length=500)
