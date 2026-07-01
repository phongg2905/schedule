from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.tasks.schemas import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from src.modules.tasks.service import TaskService

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


@router.get("", response_model=list[TaskResponse])
def list_tasks(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> list[TaskResponse]:
    service = TaskService(db, user.id)
    return [_serialize(task) for task in service.list()]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> TaskResponse:
    service = TaskService(db, user.id)
    task = service.create(payload.title, payload.description, payload.estimated_duration, payload.deadline, payload.priority, payload.tags)
    return _serialize(task)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> TaskResponse:
    service = TaskService(db, user.id)
    return _serialize(service.get(task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, payload: TaskUpdateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> TaskResponse:
    service = TaskService(db, user.id)
    return _serialize(service.update(task_id, **payload.model_dump(exclude_unset=True)))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> None:
    service = TaskService(db, user.id)
    service.delete(task_id)
