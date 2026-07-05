from src.modules.daily_plans.schemas import DailyPlanResponse, ScheduleItemResponse
from src.modules.insights.schemas import InsightResponse
from src.modules.tasks.schemas import TaskResponse


def serialize_task(task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        estimated_duration=task.estimated_duration,
        deadline=task.deadline,
        start_time=task.start_time,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        tags=task.tags,
        completed_at=task.completed_at,
    )


def serialize_task_payload(task) -> dict[str, object]:
    return serialize_task(task).model_dump()


def serialize_daily_plan(plan) -> DailyPlanResponse:
    items = [
        ScheduleItemResponse(
            id=item.id,
            label=item.label,
            start_time=item.start_time,
            end_time=item.end_time,
            status=item.status,
            task_id=item.task_id,
        )
        for schedule in getattr(plan, "schedules", []) or []
        for item in getattr(schedule, "items", []) or []
    ]
    items.sort(key=lambda item: item.start_time)
    return DailyPlanResponse(
        id=plan.id,
        plan_date=plan.plan_date,
        status=plan.status,
        source=plan.source,
        explanation=plan.explanation,
        items=items,
    )


def serialize_insight(summary) -> InsightResponse:
    payload = summary.summary_payload
    return InsightResponse(
        summary_date=payload["summary_date"],
        total_tasks=payload["total_tasks"],
        completed_tasks=payload["completed_tasks"],
        skipped_tasks=payload["skipped_tasks"],
        deferred_tasks=payload["deferred_tasks"],
        pending_tasks=payload["pending_tasks"],
        top_focus=payload["top_focus"],
        highlights=list(payload["highlights"]),
    )
