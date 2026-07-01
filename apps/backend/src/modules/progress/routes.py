from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.progress.schemas import DelayTaskRequest, MoveTaskRequest, TaskProgressRequest
from src.modules.progress.service import ProgressService
from src.modules.tasks.schemas import TaskResponse

router = APIRouter()


def _serialize(task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        estimated_duration=task.estimated_duration,
        deadline=task.deadline,
        priority=task.priority,
        status=task.status,
        tags=task.tags,
        completed_at=task.completed_at,
    )


@router.post("/tasks/{task_id}/complete", status_code=status.HTTP_200_OK)
def complete_task(task_id: str, payload: TaskProgressRequest | None = None, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict:
    service = ProgressService(db, user.id)
    task = service.complete(task_id, payload.reason if payload else None)
    return {"status": "ok", "task": _serialize(task).model_dump()}


@router.post("/tasks/{task_id}/skip", status_code=status.HTTP_200_OK)
def skip_task(task_id: str, payload: TaskProgressRequest | None = None, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict:
    service = ProgressService(db, user.id)
    task = service.skip(task_id, payload.reason if payload else None)
    return {"status": "ok", "task": _serialize(task).model_dump()}


@router.post("/tasks/{task_id}/delay", status_code=status.HTTP_200_OK)
def delay_task(task_id: str, payload: DelayTaskRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict:
    service = ProgressService(db, user.id)
    task = service.delay(task_id, payload.new_deadline, payload.reason)
    return {"status": "ok", "task": _serialize(task).model_dump()}


@router.post("/tasks/{task_id}/move", status_code=status.HTTP_200_OK)
def move_task(task_id: str, payload: MoveTaskRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> dict:
    service = ProgressService(db, user.id)
    task = service.move(task_id, payload.target_date, payload.reason)
    return {"status": "ok", "task": _serialize(task).model_dump()}
