from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.insights.schemas import InsightResponse
from src.modules.insights.service import InsightService
from src.modules.serializers import serialize_insight

router = APIRouter()


@router.get("/today", response_model=InsightResponse)
def today(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> InsightResponse:
    service = InsightService(db, user.id)
    return serialize_insight(service.today())
