from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.ai.schemas import AdjustDailyPlanRequest, ExplainDailyPlanRequest, GenerateDailyPlanRequest
from src.modules.ai.service import AIService
from src.modules.daily_plans.schemas import DailyPlanResponse
from src.modules.serializers import serialize_daily_plan

router = APIRouter()


@router.post("/generate-daily-plan", response_model=DailyPlanResponse)
def generate_daily_plan(
    payload: GenerateDailyPlanRequest,
    user=Depends(get_user_from_access_token),
    db: Session = Depends(db_session),
) -> DailyPlanResponse:
    service = AIService(db, user.id)
    plan = service.generate_daily_plan(payload.plan_date, payload.context_window_type, payload.trigger_source)
    return serialize_daily_plan(plan)


@router.post("/explain")
def explain_plan(payload: ExplainDailyPlanRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict[str, str]:
    service = AIService(db, user.id)
    explanation = service.explain_daily_plan(payload.daily_plan_id, payload.question)
    return {"daily_plan_id": payload.daily_plan_id, "explanation": explanation}


@router.post("/adjust")
def adjust(payload: AdjustDailyPlanRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict[str, str]:
    service = AIService(db, user.id)
    suggestion = service.adjust(payload.daily_plan_id, payload.change_description)
    return {"suggestion_id": suggestion.id, "explanation": suggestion.explanation}
