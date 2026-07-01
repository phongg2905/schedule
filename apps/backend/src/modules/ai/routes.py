from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.ai.schemas import AdjustDailyPlanRequest, ExplainDailyPlanRequest, GenerateDailyPlanRequest
from src.modules.ai.service import AIService
from src.modules.daily_plans.schemas import DailyPlanResponse
from src.modules.insights.schemas import InsightResponse
from src.modules.insights.service import InsightService

router = APIRouter()


@router.post("/generate-daily-plan", response_model=DailyPlanResponse)
def generate_daily_plan(payload: GenerateDailyPlanRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> DailyPlanResponse:
    service = AIService(db, user.id)
    plan = service.generate_daily_plan(payload.plan_date, payload.context_window_type, payload.trigger_source)
    return DailyPlanResponse(
        id=plan.id,
        plan_date=plan.plan_date,
        status=plan.status,
        source=plan.source,
        explanation=plan.explanation,
        items=[
            {
                "id": item.id,
                "label": item.label,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "status": item.status,
                "task_id": item.task_id,
            }
            for schedule in plan.schedules
            for item in schedule.items
        ],
    )


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


@router.post("/regenerate", response_model=DailyPlanResponse)
def regenerate(payload: GenerateDailyPlanRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> DailyPlanResponse:
    service = AIService(db, user.id)
    plan = service.generate_daily_plan(payload.plan_date, payload.context_window_type, payload.trigger_source)
    return DailyPlanResponse(
        id=plan.id,
        plan_date=plan.plan_date,
        status=plan.status,
        source=plan.source,
        explanation=plan.explanation,
        items=[
            {
                "id": item.id,
                "label": item.label,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "status": item.status,
                "task_id": item.task_id,
            }
            for schedule in plan.schedules
            for item in schedule.items
        ],
    )


@router.post("/summarize", response_model=InsightResponse)
def summarize(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> InsightResponse:
    summary = InsightService(db, user.id).today()
    payload = summary.summary_payload
    return InsightResponse(
        summary_date=payload["summary_date"],
        total_tasks=payload["total_tasks"],
        completed_tasks=payload["completed_tasks"],
        skipped_tasks=payload["skipped_tasks"],
        deferred_tasks=payload["deferred_tasks"],
        pending_tasks=payload["pending_tasks"],
        top_focus=payload["top_focus"],
        highlights=list(payload["highlights"]),
    )
