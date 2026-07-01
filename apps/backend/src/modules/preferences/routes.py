from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.preferences.schemas import PreferencesResponse, PreferencesUpdateRequest
from src.modules.preferences.service import PreferencesService

router = APIRouter()


def _serialize(preference) -> PreferencesResponse:
    return PreferencesResponse(
        timezone=preference.user.timezone,
        work_start_time=preference.work_start_time,
        work_end_time=preference.work_end_time,
        lunch_start_time=preference.lunch_start_time,
        lunch_end_time=preference.lunch_end_time,
        day_offs=preference.day_offs,
        focus_hours=preference.focus_hours,
    )


@router.get("")
def get_preferences(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> PreferencesResponse:
    service = PreferencesService(db, user.id)
    preference = service.get(user.timezone)
    return _serialize(preference)


@router.put("")
def update_preferences(payload: PreferencesUpdateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> PreferencesResponse:
    service = PreferencesService(db, user.id)
    preference = service.update(
        timezone=payload.timezone,
        work_start_time=payload.work_start_time,
        work_end_time=payload.work_end_time,
        lunch_start_time=payload.lunch_start_time,
        lunch_end_time=payload.lunch_end_time,
        day_offs=payload.day_offs,
        focus_hours=payload.focus_hours,
    )
    return _serialize(preference)
