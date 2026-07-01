from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import ActivityEvent, User, UserSchedulePreference


class PreferencesService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def get(self, user_timezone: str) -> UserSchedulePreference:
        preference = self.db.query(UserSchedulePreference).filter(UserSchedulePreference.user_id == self.user_id).one_or_none()
        if preference is None:
            user = self.db.get(User, self.user_id)
            if user is None:
                raise RuntimeError("User not found")
            preference = UserSchedulePreference(user_id=self.user_id, user=user)
            self.db.add(preference)
            self.db.commit()
            self.db.refresh(preference)
        if user_timezone and preference.user.timezone != user_timezone:
            preference.user.timezone = user_timezone
            self.db.commit()
            self.db.refresh(preference)
        return preference

    def update(
        self,
        *,
        timezone: str,
        work_start_time: str,
        work_end_time: str,
        lunch_start_time: str,
        lunch_end_time: str,
        day_offs: list[str],
        focus_hours: list[str],
    ) -> UserSchedulePreference:
        preference = self.db.query(UserSchedulePreference).filter(UserSchedulePreference.user_id == self.user_id).one_or_none()
        if preference is None:
            preference = UserSchedulePreference(user_id=self.user_id)
            self.db.add(preference)

        preference.work_start_time = work_start_time
        preference.work_end_time = work_end_time
        preference.lunch_start_time = lunch_start_time
        preference.lunch_end_time = lunch_end_time
        preference.day_offs = day_offs
        preference.focus_hours = focus_hours

        user = self.db.get(User, self.user_id)
        if user is not None:
            user.timezone = timezone

        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="preferences_updated",
                entity_type="preferences",
                entity_id=self.user_id,
                source="manual",
                payload={
                    "timezone": timezone,
                    "work_start_time": work_start_time,
                    "work_end_time": work_end_time,
                    "lunch_start_time": lunch_start_time,
                    "lunch_end_time": lunch_end_time,
                    "day_offs": day_offs,
                    "focus_hours": focus_hours,
                },
            )
        )
        self.db.commit()
        self.db.refresh(preference)
        return preference
