from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from src.db.models import ActivityEvent, ContextSnapshot, DailyPlan, Schedule, ScheduleItem, Task, UserSchedulePreference, new_id


class DailyPlanService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def today(self) -> DailyPlan | None:
        today = date.today().isoformat()
        return self.db.query(DailyPlan).filter(DailyPlan.user_id == self.user_id, DailyPlan.plan_date == today).one_or_none()

    def generate(self, plan_date: str, context_window_type: str, trigger_source: str) -> DailyPlan:
        existing_plan = self.db.query(DailyPlan).filter(DailyPlan.user_id == self.user_id, DailyPlan.plan_date == plan_date).one_or_none()
        preference = self.db.query(UserSchedulePreference).filter(UserSchedulePreference.user_id == self.user_id).one_or_none()
        tasks = self._list_candidate_tasks()
        snapshot_payload = {
            "plan_date": plan_date,
            "trigger_source": trigger_source,
            "context_window_type": context_window_type,
            "preferences": self._preferences_payload(preference),
            "candidate_task_count": len(tasks),
        }
        snapshot = ContextSnapshot(
            id=new_id(),
            user_id=self.user_id,
            snapshot_type=context_window_type,
            context_payload=snapshot_payload,
        )
        self.db.add(snapshot)

        plan = existing_plan or DailyPlan(id=new_id(), user_id=self.user_id, plan_date=plan_date, status="draft", source="rule_based")
        plan.status = "generated"
        plan.source = "rule_based"
        plan.context_snapshot_id = snapshot.id

        schedule = self.db.query(Schedule).filter(Schedule.user_id == self.user_id, Schedule.daily_plan_id == plan.id).one_or_none()
        if schedule is None:
            schedule = Schedule(id=new_id(), user_id=self.user_id, daily_plan=plan, daily_plan_id=plan.id, schedule_date=plan_date, schedule_type="day", source="rule_based")
        else:
            schedule.schedule_date = plan_date
            schedule.schedule_type = "day"
            schedule.source = "rule_based"
            for item in list(schedule.items):
                self.db.delete(item)

        scheduled_items, overflow_tasks, day_off = self._build_schedule_items(plan_date, tasks, preference, schedule.id, plan.id)
        plan.explanation = self._build_explanation(scheduled_items, overflow_tasks, preference, day_off)

        self.db.add(plan)
        self.db.add(schedule)
        for item in scheduled_items:
            self.db.add(item)

        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="daily_plan_created" if existing_plan is None else "daily_plan_updated",
                entity_type="daily_plan",
                entity_id=plan.id,
                source="system",
                payload={
                    "plan_date": plan_date,
                    "trigger_source": trigger_source,
                    "context_window_type": context_window_type,
                    "scheduled_item_count": len(scheduled_items),
                    "overflow_task_count": len(overflow_tasks),
                    "day_off": day_off,
                },
            )
        )
        for item in scheduled_items:
            self.db.add(
                ActivityEvent(
                    user_id=self.user_id,
                    event_type="schedule_item_created",
                    entity_type="schedule_item",
                    entity_id=item.id,
                    source="system",
                    payload={
                        "task_id": item.task_id,
                        "start_time": item.start_time,
                        "end_time": item.end_time,
                        "schedule_id": schedule.id,
                    },
                )
            )

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def _list_candidate_tasks(self) -> list[Task]:
        tasks = self.db.query(Task).filter(Task.user_id == self.user_id, Task.deleted_at.is_(None), Task.status != "completed").all()
        return sorted(tasks, key=self._task_sort_key)

    def _task_sort_key(self, task: Task) -> tuple[int, str, int, datetime]:
        priority_order = {"urgent": 4, "high": 3, "normal": 2, "low": 1}
        deadline = task.deadline or "9999-12-31"
        return (-priority_order.get(task.priority or "normal", 2), deadline, task.estimated_duration or 9999, task.created_at)

    def _preferences_payload(self, preference: UserSchedulePreference | None) -> dict[str, object]:
        if preference is None:
            return {
                "timezone": "Asia/Saigon",
                "work_start_time": "09:00",
                "work_end_time": "17:00",
                "lunch_start_time": "12:00",
                "lunch_end_time": "13:00",
                "day_offs": [],
                "focus_hours": [],
            }
        return {
            "timezone": preference.user.timezone,
            "work_start_time": preference.work_start_time,
            "work_end_time": preference.work_end_time,
            "lunch_start_time": preference.lunch_start_time,
            "lunch_end_time": preference.lunch_end_time,
            "day_offs": preference.day_offs,
            "focus_hours": preference.focus_hours,
        }

    def _build_schedule_items(
        self,
        plan_date: str,
        tasks: list[Task],
        preference: UserSchedulePreference | None,
        schedule_id: str,
        plan_id: str,
    ) -> tuple[list[ScheduleItem], list[Task], bool]:
        preferences = self._preferences_payload(preference)
        if self._is_day_off(plan_date, preferences["day_offs"]):
            return [], tasks, True

        work_start = self._combine_datetime(plan_date, preferences["work_start_time"])
        work_end = self._combine_datetime(plan_date, preferences["work_end_time"])
        lunch_start = self._combine_datetime(plan_date, preferences["lunch_start_time"])
        lunch_end = self._combine_datetime(plan_date, preferences["lunch_end_time"])

        scheduled_items: list[ScheduleItem] = []
        overflow_tasks: list[Task] = []
        current = work_start

        for task in tasks:
            duration = timedelta(minutes=task.estimated_duration or 30)
            if current < lunch_start and current + duration > lunch_start:
                current = lunch_end
            if current >= work_end:
                overflow_tasks.append(task)
                continue
            if current < lunch_end and current >= lunch_start:
                current = lunch_end
            end_time = current + duration
            if current < lunch_start and end_time > lunch_start:
                current = lunch_end
                end_time = current + duration
            if end_time > work_end:
                overflow_tasks.append(task)
                continue

            scheduled_items.append(
                ScheduleItem(
                    id=new_id(),
                    schedule_id=schedule_id,
                    task_id=task.id,
                    start_time=current.strftime("%Y-%m-%dT%H:%M:%S"),
                    end_time=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    label=task.title,
                    status="planned",
                    source="rule_based",
                )
            )
            task.daily_plan_id = plan_id
            current = end_time

        return scheduled_items, overflow_tasks, False

    def _is_day_off(self, plan_date: str, day_offs: list[str]) -> bool:
        weekday = datetime.fromisoformat(f"{plan_date}T00:00:00").strftime("%A")
        return weekday in day_offs

    def _combine_datetime(self, plan_date: str, time_value: str) -> datetime:
        return datetime.strptime(f"{plan_date} {time_value}", "%Y-%m-%d %H:%M")

    def _build_explanation(self, scheduled_items: list[ScheduleItem], overflow_tasks: list[Task], preference: UserSchedulePreference | None, day_off: bool) -> str:
        if day_off:
            return "Today is configured as a day off, so no tasks were scheduled."
        work_start_time = preference.work_start_time if preference else "09:00"
        work_end_time = preference.work_end_time if preference else "17:00"
        base = f"Rule-based plan generated from current tasks within {work_start_time} to {work_end_time}. Scheduled {len(scheduled_items)} task(s)."
        if overflow_tasks:
            base += f" {len(overflow_tasks)} task(s) did not fit today and remain unscheduled."
        return base
