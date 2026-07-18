from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.db.models import ActivityEvent, Task, new_id


class TaskService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def list(self) -> list[Task]:
        return self.db.query(Task).filter(Task.user_id == self.user_id, Task.deleted_at.is_(None)).order_by(Task.created_at.desc()).all()

    def get_history(self, from_date: str, to_date: str) -> dict:
        tasks = (
            self.db.query(Task)
            .filter(
                Task.user_id == self.user_id,
                Task.deleted_at.is_(None),
                Task.deadline.isnot(None),
                Task.deadline >= from_date,
                Task.deadline <= to_date,
            )
            .order_by(Task.deadline.asc(), Task.start_time.asc().nullslast())
            .all()
        )

        from src.modules.serializers import serialize_task

        days_map: dict[str, dict] = {}
        total_completed = 0
        total_pending = 0

        for task in tasks:
            d = task.deadline
            if d not in days_map:
                days_map[d] = {"date": d, "total": 0, "completed": 0, "pending": 0, "tasks": []}
            days_map[d]["total"] += 1
            if task.status == "completed":
                days_map[d]["completed"] += 1
                total_completed += 1
            else:
                days_map[d]["pending"] += 1
                total_pending += 1
            days_map[d]["tasks"].append(serialize_task(task))

        sorted_days = sorted(days_map.values(), key=lambda x: x["date"], reverse=True)

        return {
            "days": sorted_days,
            "from_date": from_date,
            "to_date": to_date,
            "total_tasks": len(tasks),
            "total_completed": total_completed,
            "total_pending": total_pending,
        }

    def create(
        self,
        title: str,
        description: str | None,
        estimated_duration: int | None,
        deadline: str | None,
        start_time: str | None,
        task_type: str,
        priority: str | None,
        tags: list[str],
    ) -> Task:
        self._validate_time_overlap(start_time, estimated_duration, task_type, exclude_task_id=None)
        task = Task(
            id=new_id(),
            user_id=self.user_id,
            title=title,
            description=description,
            estimated_duration=estimated_duration,
            deadline=deadline,
            start_time=start_time,
            task_type=task_type,
            priority=priority or "normal",
            tags=tags,
            status="todo",
            completed_at=None,
        )
        self.db.add(task)
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="task_created",
                entity_type="task",
                entity_id=task.id,
                source="manual",
                payload={
                    "title": title,
                    "task_type": task_type,
                    "priority": priority or "normal",
                    "deadline": deadline,
                    "start_time": start_time,
                    "estimated_duration": estimated_duration,
                    "tags": tags,
                    "source": "manual",
                },
            )
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, task_id: str) -> Task:
        task = self.db.get(Task, task_id)
        if not task or task.user_id != self.user_id or task.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TASK_NOT_FOUND")
        return task

    def update(self, task_id: str, **fields) -> Task:
        task = self.get(task_id)
        start_time = fields.get("start_time", task.start_time)
        estimated_duration = fields.get("estimated_duration", task.estimated_duration)
        task_type = fields.get("task_type", task.task_type)
        self._validate_time_overlap(start_time, estimated_duration, task_type, exclude_task_id=task_id)
        for key, value in fields.items():
            setattr(task, key, value)
        if "status" in fields and fields["status"] is not None:
            if task.status == "completed" and task.completed_at is None:
                task.completed_at = datetime.now(UTC)
            elif task.status != "completed" and task.completed_at is not None:
                task.completed_at = None
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="task_updated",
                entity_type="task",
                entity_id=task.id,
                source="manual",
                payload={"fields": {k: v for k, v in fields.items() if v is not None}},
            )
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task_id: str) -> None:
        task = self.get(task_id)
        task.deleted_at = datetime.now(UTC)
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="task_deleted",
                entity_type="task",
                entity_id=task.id,
                source="manual",
                payload={"task_id": task.id},
            )
        )
        self.db.commit()

    def _validate_time_overlap(
        self,
        start_time: str | None,
        estimated_duration: int | None,
        task_type: str,
        exclude_task_id: str | None,
    ) -> None:
        if task_type == "flexible":
            return
        if not start_time or not estimated_duration:
            return
        new_start_minutes = self._time_to_minutes(start_time)
        new_end_minutes = new_start_minutes + estimated_duration

        query = self.db.query(Task).filter(
            Task.user_id == self.user_id,
            Task.deleted_at.is_(None),
            Task.task_type == "scheduled",
            Task.start_time.isnot(None),
            Task.estimated_duration.isnot(None),
        )
        if exclude_task_id:
            query = query.filter(Task.id != exclude_task_id)

        conflicting = query.all()
        for existing in conflicting:
            existing_start = self._time_to_minutes(existing.start_time)
            existing_end = existing_start + existing.estimated_duration
            if existing_start < new_end_minutes and existing_end > new_start_minutes:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="TASK_TIME_CONFLICT",
                )

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    @staticmethod
    def _minutes_to_time(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
