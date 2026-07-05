from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.db.models import ActivityEvent, Feedback, new_id
from src.modules.feedback.schemas import FeedbackCreateRequest

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict[str, str]:
    feedback = Feedback(
        id=new_id(), user_id=user.id,
        target_type=payload.target_type, target_id=payload.target_id,
        rating=payload.rating, note=payload.note,
    )
    db.add(feedback)
    db.add(
        ActivityEvent(
            user_id=user.id,
            event_type="feedback_submitted",
            entity_type=payload.target_type,
            entity_id=payload.target_id,
            source="manual",
            payload={"rating": payload.rating, "note": payload.note},
        )
    )
    db.commit()
    return {"status": "ok", "feedback_id": feedback.id}
