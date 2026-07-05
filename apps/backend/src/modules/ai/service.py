from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.models import (
    ActivityEvent,
    AISuggestion,
    ContextSnapshot,
    DailyPlan,
    Schedule,
    ScheduleItem,
    Task,
    UserPreference,
    UserSchedulePreference,
    new_id,
)
from src.modules.ai.provider import LocalDailyPlanAIProvider, build_daily_plan_provider
from src.modules.daily_plans.service import DailyPlanService


class AIService:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def generate_daily_plan(self, plan_date: str, context_window_type: str, trigger_source: str) -> DailyPlan:
        planner = DailyPlanService(self.db, self.user_id)
        preference = self.db.query(UserSchedulePreference).filter(UserSchedulePreference.user_id == self.user_id).one_or_none()
        language = self._get_language()
        tasks = planner._list_candidate_tasks()
        provider = build_daily_plan_provider(get_settings().openai_api_key)
        context = self._build_generation_context(
            planner=planner,
            plan_date=plan_date,
            context_window_type=context_window_type,
            trigger_source=trigger_source,
            language=language,
            preference=preference,
            tasks=tasks,
        )
        try:
            ranking = provider.rank_tasks(context)
        except ValueError:
            ranking = LocalDailyPlanAIProvider().rank_tasks(context)
        ordered_tasks = self._order_tasks(tasks, ranking.ordered_task_ids)

        existing_plan = self.db.query(DailyPlan).filter(DailyPlan.user_id == self.user_id, DailyPlan.plan_date == plan_date).one_or_none()
        snapshot = ContextSnapshot(
            id=new_id(),
            user_id=self.user_id,
            snapshot_type=context_window_type,
            context_payload={**context, "provider": provider.__class__.__name__, "ordered_task_ids": ranking.ordered_task_ids},
        )
        self.db.add(snapshot)

        plan = existing_plan or DailyPlan(id=new_id(), user_id=self.user_id, plan_date=plan_date, status="draft", source="ai")
        plan.status = "generated"
        plan.source = "ai"
        plan.context_snapshot_id = snapshot.id

        schedule = self.db.query(Schedule).filter(Schedule.user_id == self.user_id, Schedule.daily_plan_id == plan.id).one_or_none()
        if schedule is None:
            schedule = Schedule(
                id=new_id(), user_id=self.user_id,
                daily_plan_id=plan.id, schedule_date=plan_date,
                schedule_type="day", source="ai",
            )
        else:
            schedule.schedule_date = plan_date
            schedule.schedule_type = "day"
            schedule.source = "ai"
            for item in list(schedule.items):
                self.db.delete(item)

        scheduled_items, overflow_tasks, day_off = planner._build_schedule_items(
            plan_date, ordered_tasks, preference, schedule.id, plan.id,
        )
        plan.explanation = self._build_explanation(ranking.explanation, scheduled_items, overflow_tasks, preference, day_off)

        self.db.add(plan)
        self.db.add(schedule)
        for item in scheduled_items:
            self.db.add(item)

        self.db.add(
            AISuggestion(
                id=new_id(),
                user_id=self.user_id,
                daily_plan=plan,
                daily_plan_id=plan.id,
                context_snapshot_id=snapshot.id,
                suggestion_type="daily_plan_generation",
                explanation=plan.explanation or ranking.explanation,
                status="draft",
            )
        )
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="ai_schedule_requested",
                entity_type="daily_plan",
                entity_id=plan.id,
                source="system",
                payload={"plan_date": plan_date, "trigger_source": trigger_source, "context_window_type": context_window_type},
            )
        )
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="ai_schedule_generated",
                entity_type="daily_plan",
                entity_id=plan.id,
                source="ai",
                payload={
                    "plan_date": plan_date,
                    "context_snapshot_id": snapshot.id,
                    "daily_plan_id": plan.id,
                    "scheduled_item_count": len(scheduled_items),
                    "overflow_task_count": len(overflow_tasks),
                },
            )
        )

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def explain_daily_plan(self, daily_plan_id: str, question: str) -> str:
        plan = self.db.get(DailyPlan, daily_plan_id)
        if not plan or plan.user_id != self.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DAILY_PLAN_NOT_FOUND")

        provider = build_daily_plan_provider(get_settings().openai_api_key)
        context = self._build_explanation_context(plan=plan, question=question, language=self._get_language())
        try:
            explanation = provider.explain_plan(context)
        except ValueError:
            explanation = LocalDailyPlanAIProvider().explain_plan(context)

        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="ai_schedule_requested",
                entity_type="daily_plan",
                entity_id=plan.id,
                source="system",
                payload={"question": question, "mode": "explanation"},
            )
        )
        self.db.commit()
        return explanation

    def adjust(self, daily_plan_id: str, change_description: str) -> AISuggestion:
        plan = self.db.get(DailyPlan, daily_plan_id)
        if not plan or plan.user_id != self.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DAILY_PLAN_NOT_FOUND")

        planner = DailyPlanService(self.db, self.user_id)
        preference = self.db.query(UserSchedulePreference).filter(UserSchedulePreference.user_id == self.user_id).one_or_none()
        provider = build_daily_plan_provider(get_settings().openai_api_key)
        context = self._build_adjustment_context(
            planner=planner,
            plan=plan,
            daily_plan_id=daily_plan_id,
            change_description=change_description,
            language=self._get_language(),
            preference=preference,
        )
        try:
            adjustment = provider.adjust_plan(context)
        except ValueError:
            adjustment = LocalDailyPlanAIProvider().adjust_plan(context)

        snapshot = ContextSnapshot(
            id=new_id(),
            user_id=self.user_id,
            snapshot_type="adjustment",
            context_payload={**context, "provider": provider.__class__.__name__},
        )
        suggestion = AISuggestion(
            id=new_id(),
            user_id=self.user_id,
            daily_plan=plan,
            context_snapshot_id=snapshot.id,
            suggestion_type="adjustment",
            explanation=f"{adjustment.suggestion} {adjustment.explanation}".strip(),
            status="draft",
        )
        self.db.add(snapshot)
        self.db.add(suggestion)
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="ai_adjustment_requested",
                entity_type="daily_plan",
                entity_id=daily_plan_id,
                source="system",
                payload={"change_description": change_description},
            )
        )
        self.db.add(
            ActivityEvent(
                user_id=self.user_id,
                event_type="ai_adjustment_created",
                entity_type="ai_suggestion",
                entity_id=suggestion.id,
                source="ai",
                payload={"daily_plan_id": daily_plan_id, "change_description": change_description},
            )
        )
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def _order_tasks(self, tasks: list[Task], ordered_task_ids: list[str]) -> list[Task]:
        task_map = {task.id: task for task in tasks}
        ordered_tasks = [task_map[task_id] for task_id in ordered_task_ids if task_id in task_map]
        if len(ordered_tasks) != len(tasks):
            remaining = [task for task in tasks if task.id not in ordered_task_ids]
            ordered_tasks.extend(remaining)
        return ordered_tasks

    def _get_language(self) -> str:
        language_preference = self.db.query(UserPreference).filter(UserPreference.user_id == self.user_id).one_or_none()
        return language_preference.language if language_preference else "en"

    def _build_generation_context(
        self,
        *,
        planner: DailyPlanService,
        plan_date: str,
        context_window_type: str,
        trigger_source: str,
        language: str,
        preference: UserSchedulePreference | None,
        tasks: list[Task],
    ) -> dict:
        return {
            "plan_date": plan_date,
            "trigger_source": trigger_source,
            "context_window_type": context_window_type,
            "language": language,
            "preferences": planner._preferences_payload(preference),
            "tasks": [self._task_context(task) for task in tasks],
        }

    def _build_explanation_context(self, *, plan: DailyPlan, question: str, language: str) -> dict:
        return {
            "question": question,
            "language": language,
            "plan": self._plan_context(plan),
        }

    def _build_adjustment_context(
        self,
        *,
        planner: DailyPlanService,
        plan: DailyPlan,
        daily_plan_id: str,
        change_description: str,
        language: str,
        preference: UserSchedulePreference | None,
    ) -> dict:
        return {
            "daily_plan_id": daily_plan_id,
            "change_description": change_description,
            "language": language,
            "preferences": planner._preferences_payload(preference),
            "plan": self._plan_context(plan),
        }

    def _plan_context(self, plan: DailyPlan) -> dict:
        return {
            "id": plan.id,
            "plan_date": plan.plan_date,
            "source": plan.source,
            "explanation": plan.explanation,
            "items": [self._schedule_item_context(item) for schedule in plan.schedules for item in schedule.items],
        }

    def _task_context(self, task: Task) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "deadline": task.deadline,
            "priority": task.priority,
            "estimated_duration": task.estimated_duration,
            "tags": task.tags,
        }

    def _schedule_item_context(self, item: ScheduleItem) -> dict:
        return {
            "id": item.id,
            "label": item.label,
            "start_time": item.start_time,
            "end_time": item.end_time,
            "status": item.status,
            "task_id": item.task_id,
        }

    def _build_explanation(
        self,
        provider_explanation: str,
        scheduled_items: list[ScheduleItem],
        overflow_tasks: list[Task],
        preference: UserSchedulePreference | None,
        day_off: bool,
    ) -> str:
        if day_off:
            return "Today is configured as a day off, so no AI schedule was produced."
        work_start_time = preference.work_start_time if preference else "09:00"
        work_end_time = preference.work_end_time if preference else "17:00"
        base = provider_explanation or f"AI generated a plan within {work_start_time} to {work_end_time}."
        if scheduled_items:
            base += f" Scheduled {len(scheduled_items)} task(s)."
        if overflow_tasks:
            base += f" {len(overflow_tasks)} task(s) did not fit today."
        return base
