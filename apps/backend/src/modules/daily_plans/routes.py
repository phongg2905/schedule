from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.db.models import DailyPlan
from src.modules.daily_plans.schemas import DailyPlanDraftRequest, DailyPlanGenerateRequest, DailyPlanResponse
from src.modules.daily_plans.service import DailyPlanService
from src.modules.serializers import serialize_daily_plan

router = APIRouter()


@router.get("/today", response_model=DailyPlanResponse | None)
def get_today(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    service = DailyPlanService(db, user.id)
    plan = service.today()
    return serialize_daily_plan(plan) if plan else None


@router.post("/generate", response_model=DailyPlanResponse, status_code=status.HTTP_201_CREATED)
def generate(payload: DailyPlanGenerateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    service = DailyPlanService(db, user.id)
    plan = service.generate(payload.plan_date, payload.context_window_type, payload.trigger_source)
    return serialize_daily_plan(plan)


@router.post("/draft", response_model=DailyPlanResponse, status_code=status.HTTP_201_CREATED)
def draft(payload: DailyPlanDraftRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    service = DailyPlanService(db, user.id)
    plan = service.draft(payload.plan_date, payload.context_window_type, payload.trigger_source)
    return serialize_daily_plan(plan)


@router.post("/{plan_id}/confirm", response_model=DailyPlanResponse)
def confirm(plan_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    service = DailyPlanService(db, user.id)
    plan = service.confirm(plan_id)
    return serialize_daily_plan(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard(plan_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> None:
    service = DailyPlanService(db, user.id)
    service.discard(plan_id)


@router.post("/{plan_id}/complete")
def complete(plan_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    plan = db.get(DailyPlan, plan_id)
    if plan and plan.user_id == user.id:
        plan.status = "completed"
        db.commit()
    return {"status": "ok"}
