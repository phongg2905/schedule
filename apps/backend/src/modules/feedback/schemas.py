from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    target_type: str = Field(min_length=1, max_length=50)
    target_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    note: str | None = None
