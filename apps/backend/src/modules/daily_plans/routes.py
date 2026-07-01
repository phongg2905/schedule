from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.db.models import DailyPlan
from src.modules.daily_plans.schemas import DailyPlanGenerateRequest, DailyPlanResponse, ScheduleItemResponse
from src.modules.daily_plans.service import DailyPlanService

router = APIRouter()


def _serialize(plan) -> DailyPlanResponse:
    items: list[ScheduleItemResponse] = []
    for schedule in getattr(plan, "schedules", []) or []:
        for item in getattr(schedule, "items", []) or []:
            items.append(
                ScheduleItemResponse(
                    id=item.id,
                    label=item.label,
                    start_time=item.start_time,
                    end_time=item.end_time,
                    status=item.status,
                    task_id=item.task_id,
                )
            )
    return DailyPlanResponse(id=plan.id, plan_date=plan.plan_date, status=plan.status, source=plan.source, explanation=plan.explanation, items=items)


@router.get("/today", response_model=DailyPlanResponse | None)
def get_today(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    service = DailyPlanService(db, user.id)
    plan = service.today()
    return _serialize(plan) if plan else None


@router.post("/generate", response_model=DailyPlanResponse, status_code=status.HTTP_201_CREATED)
def generate(payload: DailyPlanGenerateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    service = DailyPlanService(db, user.id)
    plan = service.generate(payload.plan_date, payload.context_window_type, payload.trigger_source)
    return _serialize(plan)


@router.post("/{plan_id}/complete")
def complete(plan_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)):
    plan = db.get(DailyPlan, plan_id)
    if plan and plan.user_id == user.id:
        plan.status = "completed"
        db.commit()
    return {"status": "ok"}
