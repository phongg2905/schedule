from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models import ActivityEvent, DailyPlan, Schedule, Task


class ProgressService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def complete(self, task_id: str, reason: str | None = None) -> Task:
        task = self._get_task(task_id)
        if task.status == "completed":
            return task
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        self._sync_schedule_item(task, "completed")
        self._log_event("task_completed", task, {"reason": reason})
        self._maybe_complete_daily_plan(task.daily_plan_id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def skip(self, task_id: str, reason: str | None = None) -> Task:
        task = self._get_task(task_id)
        self._ensure_not_completed(task)
        task.status = "skipped"
        task.completed_at = None
        self._sync_schedule_item(task, "skipped")
        self._log_event("task_skipped", task, {"reason": reason})
        self._maybe_complete_daily_plan(task.daily_plan_id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delay(self, task_id: str, new_deadline: str | None, reason: str | None = None) -> Task:
        task = self._get_task(task_id)
        self._ensure_not_completed(task)
        task.status = "deferred"
        task.completed_at = None
        if new_deadline:
            task.deadline = new_deadline
        self._sync_schedule_item(task, "deferred")
        self._log_event("task_delayed", task, {"reason": reason, "new_deadline": new_deadline})
        self._maybe_complete_daily_plan(task.daily_plan_id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def move(self, task_id: str, target_date: str, reason: str | None = None) -> Task:
        task = self._get_task(task_id)
        self._ensure_not_completed(task)
        task.status = "todo"
        task.completed_at = None
        task.deadline = target_date
        self._sync_schedule_item(task, "moved")
        self._log_event("task_moved", task, {"reason": reason, "target_date": target_date})
        self._maybe_complete_daily_plan(task.daily_plan_id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def _get_task(self, task_id: str) -> Task:
        task = self.db.get(Task, task_id)
        if not task or task.user_id != self.user_id or task.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TASK_NOT_FOUND")
        return task

    def _ensure_not_completed(self, task: Task) -> None:
        if task.status == "completed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TASK_ALREADY_COMPLETED")

    def _sync_schedule_item(self, task: Task, status_value: str) -> None:
        if not task.daily_plan_id:
            return
        schedule = (
            self.db.query(Schedule)
            .filter(Schedule.user_id == self.user_id, Schedule.daily_plan_id == task.daily_plan_id)
            .one_or_none()
        )
        if schedule is None:
            return
        item = next((item for item in schedule.items if item.task_id == task.id), None)
        if item is None:
            return
        item.status = status_value
        self.db.add(item)
        self._log_event(
            "schedule_item_updated",
            task,
            {
                "schedule_item_id": item.id,
                "schedule_id": schedule.id,
                "status": status_value,
            },
            entity_type="schedule_item",
            entity_id=item.id,
        )

    def _maybe_complete_daily_plan(self, daily_plan_id: str | None) -> None:
        if not daily_plan_id:
            return
        plan = self.db.get(DailyPlan, daily_plan_id)
        if not plan or plan.user_id != self.user_id:
            return
        schedule = next((schedule for schedule in plan.schedules if schedule.items), None)
        if schedule is None:
            plan.status = "completed"
            self._log_event("daily_plan_completed", plan, {"daily_plan_id": plan.id}, entity_type="daily_plan", entity_id=plan.id)
            return
        terminal_statuses = {"completed", "skipped", "moved", "deferred"}
        if all(item.status in terminal_statuses for schedule in plan.schedules for item in schedule.items if item.task_id is not None):
            plan.status = "completed"
            self._log_event("daily_plan_completed", plan, {"daily_plan_id": plan.id}, entity_type="daily_plan", entity_id=plan.id)

    def _log_event(
        self,
        event_type: str,
        target: Task | DailyPlan,
        payload: dict,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> None:
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type=event_type,
                entity_type=entity_type or target.__class__.__name__.lower(),
                entity_id=entity_id or getattr(target, "id", None),
                source="manual",
                payload=payload,
            )
        )
