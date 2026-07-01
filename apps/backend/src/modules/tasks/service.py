from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models import ActivityEvent, Task, new_id


class TaskService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def list(self) -> list[Task]:
        return self.db.query(Task).filter(Task.user_id == self.user_id, Task.deleted_at.is_(None)).order_by(Task.created_at.desc()).all()

    def create(
        self,
        title: str,
        description: str | None,
        estimated_duration: int | None,
        deadline: str | None,
        priority: str | None,
        tags: list[str],
    ) -> Task:
        task = Task(
            id=new_id(),
            user_id=self.user_id,
            title=title,
            description=description,
            estimated_duration=estimated_duration,
            deadline=deadline,
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
                    "priority": priority or "normal",
                    "deadline": deadline,
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def update(self, task_id: str, **fields) -> Task:
        task = self.get(task_id)
        for key, value in fields.items():
            if value is not None:
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
