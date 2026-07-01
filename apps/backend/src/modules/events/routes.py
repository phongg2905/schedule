from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.dependencies import db_session, get_user_from_access_token
from src.db.models import ActivityEvent, new_id

router = APIRouter()


class EventCreateRequest(BaseModel):
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    source: str = "manual"
    payload: dict = Field(default_factory=dict)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict[str, str]:
    event = ActivityEvent(
        id=new_id(),
        user_id=user.id,
        event_type=payload.event_type,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        source=payload.source,
        payload=payload.payload,
    )
    db.add(event)
    db.commit()
    return {"status": "ok", "event_id": event.id}


@router.get("")
def list_events(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> list[dict]:
    events = db.query(ActivityEvent).filter(ActivityEvent.user_id == user.id).order_by(ActivityEvent.occurred_at.desc()).limit(100).all()
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "source": event.source,
            "payload": event.payload,
            "occurred_at": event.occurred_at.isoformat(),
        }
        for event in events
    ]
