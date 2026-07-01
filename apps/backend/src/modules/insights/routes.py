from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.insights.schemas import InsightResponse
from src.modules.insights.service import InsightService

router = APIRouter()


@router.get("/today", response_model=InsightResponse)
def today(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> InsightResponse:
    service = InsightService(db, user.id)
    summary = service.today()
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

