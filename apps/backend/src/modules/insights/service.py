from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.db.models import ActivityEvent, DaySummary, DailyPlan, Task


class InsightService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def today(self) -> DaySummary:
        summary_date = date.today().isoformat()
        existing = self.db.query(DaySummary).filter(DaySummary.user_id == self.user_id, DaySummary.summary_date == summary_date).one_or_none()
        payload = self._build_payload(summary_date)
        payload_changed = existing is None or existing.summary_payload != payload
        if existing is None:
            summary = DaySummary(user_id=self.user_id, summary_date=summary_date, summary_payload=payload)
            self.db.add(summary)
        else:
            existing.summary_payload = payload
            summary = existing
        if payload_changed:
            self.db.add(
                ActivityEvent(
                    user_id=self.user_id,
                    event_type="day_summary_generated",
                    entity_type="day_summary",
                    entity_id=summary.id,
                    source="system",
                    payload=payload,
                )
            )
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def _build_payload(self, summary_date: str) -> dict:
        tasks = self.db.query(Task).filter(Task.user_id == self.user_id, Task.deleted_at.is_(None)).all()
        completed = [task for task in tasks if task.status == "completed" and task.completed_at and task.completed_at.date().isoformat() == summary_date]
        skipped = [task for task in tasks if task.status == "skipped"]
        deferred = [task for task in tasks if task.status == "deferred"]
        pending = [task for task in tasks if task.status in {"todo", "in_progress"}]
        plans_today = self.db.query(DailyPlan).filter(DailyPlan.user_id == self.user_id, DailyPlan.plan_date == summary_date).all()
        focus = "Morning focus block protected" if completed else "Start with the highest priority task"
        highlights = [
            f"Completed {len(completed)} task(s) today.",
            f"Skipped {len(skipped)} task(s) and deferred {len(deferred)} task(s).",
        ]
        if plans_today:
            highlights.append(f"Generated {len(plans_today)} daily plan record(s) for today.")
        if completed:
            highlights.append(f"First completed task: {completed[0].title}.")
        return {
            "summary_date": summary_date,
            "total_tasks": len(tasks),
            "completed_tasks": len(completed),
            "skipped_tasks": len(skipped),
            "deferred_tasks": len(deferred),
            "pending_tasks": len(pending),
            "top_focus": focus,
            "highlights": highlights,
        }
