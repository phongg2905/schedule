from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.tasks.schemas import HistoryResponse, TaskCreateRequest, TaskResponse, TaskUpdateRequest
from src.modules.tasks.service import TaskService
from src.modules.serializers import serialize_task

router = APIRouter()


@router.get("", response_model=list[TaskResponse])
def list_tasks(user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> list[TaskResponse]:
    service = TaskService(db, user.id)
    return [serialize_task(task) for task in service.list()]


@router.get("/history", response_model=HistoryResponse)
def get_history(
    from_date: str = Query(default=None, description="Start date (YYYY-MM-DD), defaults to 30 days ago from yesterday"),
    to_date: str = Query(default=None, description="End date (YYYY-MM-DD), defaults to yesterday"),
    user=Depends(get_user_from_access_token),
    db: Session = Depends(db_session),
) -> HistoryResponse:
    from datetime import date, timedelta

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if to_date is None:
        to_date = yesterday
    if from_date is None:
        from_date = (date.today() - timedelta(days=30)).isoformat()
    service = TaskService(db, user.id)
    return HistoryResponse(**service.get_history(from_date, to_date))


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateRequest, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> TaskResponse:
    service = TaskService(db, user.id)
    task = service.create(
        payload.title,
        payload.description,
        payload.estimated_duration,
        payload.deadline,
        payload.start_time,
        payload.task_type,
        payload.priority,
        payload.tags,
    )
    return serialize_task(task)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> TaskResponse:
    service = TaskService(db, user.id)
    return serialize_task(service.get(task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    payload: TaskUpdateRequest,
    user=Depends(get_user_from_access_token),
    db: Session = Depends(db_session),
) -> TaskResponse:
    service = TaskService(db, user.id)
    return serialize_task(service.update(task_id, **payload.model_dump(exclude_unset=True)))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, user=Depends(get_user_from_access_token), db: Session = Depends(db_session)) -> None:
    service = TaskService(db, user.id)
    service.delete(task_id)
