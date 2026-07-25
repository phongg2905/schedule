from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.models import (
    ActivityEvent,
    AISuggestion,
    ContextSnapshot,
    DailyPlan,
    Feedback,
    Schedule,
    ScheduleItem,
    Task,
    UserPreference,
    UserSchedulePreference,
    new_id,
)
from src.modules.ai.provider import (
    DailyPlanResult,
    LocalDailyPlanAIProvider,
    ScheduleItemResult,
    build_daily_plan_provider,
)
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
            plan_date=plan_date,
            context_window_type=context_window_type,
            trigger_source=trigger_source,
            language=language,
            preference=preference,
            tasks=tasks,
        )
        try:
            result = provider.generate_daily_plan(context)
        except ValueError:
            result = LocalDailyPlanAIProvider().generate_daily_plan(context)

        # Validate and create schedule items from AI result
        validated_items, overflow_tasks = self._validate_ai_schedule(
            plan_date=plan_date,
            result=result,
            tasks=tasks,
            preference=preference,
        )

        existing_plan = self.db.query(DailyPlan).filter(DailyPlan.user_id == self.user_id, DailyPlan.plan_date == plan_date).one_or_none()
        snapshot = ContextSnapshot(
            id=new_id(),
            user_id=self.user_id,
            snapshot_type=context_window_type,
            context_payload={
                **context,
                "provider": provider.__class__.__name__,
                "ai_status": result.status,
                "ai_confidence": result.confidence,
                "ordered_task_ids": result.ordered_task_ids,
                "overflow_task_ids": result.overflow_task_ids,
                "highlights": result.highlights,
            },
        )
        self.db.add(snapshot)

        plan = existing_plan or DailyPlan(id=new_id(), user_id=self.user_id, plan_date=plan_date, status="draft", source="ai")
        plan.status = "generated"
        plan.source = "ai"
        plan.context_snapshot_id = snapshot.id
        plan.explanation = result.explanation

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

        self.db.add(plan)
        self.db.add(schedule)
        for item in validated_items:
            item.schedule_id = schedule.id
            self.db.add(item)

        # Save overflow info to DailyPlan explanation if missing
        if overflow_tasks and plan.explanation:
            plan.explanation += f" {len(overflow_tasks)} task(s) could not fit today."

        self.db.add(
            AISuggestion(
                id=new_id(),
                user_id=self.user_id,
                daily_plan=plan,
                daily_plan_id=plan.id,
                context_snapshot_id=snapshot.id,
                suggestion_type="daily_plan_generation",
                explanation=result.explanation,
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
                    "ai_status": result.status,
                    "ai_confidence": result.confidence,
                    "scheduled_item_count": len(validated_items),
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

    def _validate_ai_schedule(
        self,
        *,
        plan_date: str,
        result: DailyPlanResult,
        tasks: list[Task],
        preference: UserSchedulePreference | None,
    ) -> tuple[list[ScheduleItem], list[str]]:
        """Validate AI-generated schedule against hard constraints."""
        # Handle day_off
        if result.status == "day_off":
            return [], [task.id for task in tasks]

        pref_payload = {
            "work_start_time": preference.work_start_time if preference else "09:00",
            "work_end_time": preference.work_end_time if preference else "17:00",
            "lunch_start_time": preference.lunch_start_time if preference else "12:00",
            "lunch_end_time": preference.lunch_end_time if preference else "13:00",
            "day_offs": preference.day_offs if preference else [],
        }

        # Check day off
        weekday = datetime.fromisoformat(f"{plan_date}T00:00:00").strftime("%A")
        if weekday in pref_payload["day_offs"]:
            return [], [task.id for task in tasks]

        work_start_mins = self._time_str_to_mins(pref_payload["work_start_time"])
        work_end_mins = self._time_str_to_mins(pref_payload["work_end_time"])
        lunch_start_mins = self._time_str_to_mins(pref_payload["lunch_start_time"])
        lunch_end_mins = self._time_str_to_mins(pref_payload["lunch_end_time"])

        task_map = {task.id: task for task in tasks}
        validated_items: list[ScheduleItem] = []
        overflow_task_ids: list[str] = []

        for sched_item in result.schedule_items:
            task_id = sched_item.task_id
            task = task_map.get(task_id)

            # Skip if task not found
            if not task:
                overflow_task_ids.append(task_id)
                continue

            # Extract time from AI output
            try:
                start_mins = self._time_str_to_mins(sched_item.start_time[11:16])
                end_mins = self._time_str_to_mins(sched_item.end_time[11:16])
            except (ValueError, IndexError):
                overflow_task_ids.append(task_id)
                continue

            duration = end_mins - start_mins

            # Validate: must be within work hours
            if start_mins < work_start_mins or end_mins > work_end_mins:
                overflow_task_ids.append(task_id)
                continue

            # Validate: must not overlap with lunch
            if start_mins < lunch_end_mins and end_mins > lunch_start_mins:
                # Allow lunch to be within if it wraps around
                if not (start_mins >= lunch_start_mins and end_mins <= lunch_end_mins):
                    # Shift after lunch
                    new_start = max(start_mins, lunch_end_mins)
                    end_mins = new_start + duration
                    if end_mins > work_end_mins:
                        overflow_task_ids.append(task_id)
                        continue
                    start_mins = new_start

            # Validate: no overlap with previously scheduled items
            conflict = False
            for existing in validated_items:
                e_start = self._time_str_to_mins(existing.start_time[11:16])
                e_end = self._time_str_to_mins(existing.end_time[11:16])
                if start_mins < e_end and end_mins > e_start:
                    conflict = True
                    break
            if conflict:
                overflow_task_ids.append(task_id)
                continue

            validated_items.append(
                ScheduleItem(
                    id=new_id(),
                    schedule_id="",  # Will be set by caller
                    task_id=task_id,
                    start_time=sched_item.start_time,
                    end_time=sched_item.end_time,
                    label=sched_item.label,
                    status="planned",
                    source="ai",
                )
            )

        # Add any remaining overflow from AI result
        for task_id in result.overflow_task_ids:
            task = task_map.get(task_id)
            if task and task.id not in [item.task_id for item in validated_items]:
                if task.id not in overflow_task_ids:
                    overflow_task_ids.append(task.id)

        return validated_items, overflow_task_ids

    def _get_language(self) -> str:
        language_preference = self.db.query(UserPreference).filter(UserPreference.user_id == self.user_id).one_or_none()
        return language_preference.language if language_preference else "en"

    def _build_generation_context(
        self,
        *,
        plan_date: str,
        context_window_type: str,
        trigger_source: str,
        language: str,
        preference: UserSchedulePreference | None,
        tasks: list[Task],
    ) -> dict:
        from src.db.models import User
        user = self.db.get(User, self.user_id)

        profile = {
            "name": user.name if user else "",
            "timezone": user.timezone if user else "Asia/Saigon",
            "role": user.role if user else "user",
        }

        preferences = self._preferences_payload(preference)

        # Gather recent feedback (last 30 days)
        thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        recent_feedback = self.db.query(Feedback).filter(
            Feedback.user_id == self.user_id,
            Feedback.created_at >= thirty_days_ago,
        ).all()
        feedback_list = [
            {"target_type": fb.target_type, "target_id": fb.target_id, "rating": fb.rating, "note": fb.note}
            for fb in recent_feedback
        ]

        # Gather recent activity events (last 7 days)
        seven_days_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        recent_events = self.db.query(ActivityEvent).filter(
            ActivityEvent.user_id == self.user_id,
            ActivityEvent.occurred_at >= seven_days_ago,
        ).order_by(ActivityEvent.occurred_at.desc()).limit(50).all()
        events_list = [
            {"event_type": ev.event_type, "entity_type": ev.entity_type, "entity_id": ev.entity_id, "source": ev.source, "occurred_at": ev.occurred_at.isoformat()}
            for ev in recent_events
        ]

        # Get current schedule for today
        current_plan = self.db.query(DailyPlan).filter(
            DailyPlan.user_id == self.user_id,
            DailyPlan.plan_date == plan_date,
        ).one_or_none()
        current_schedule = self._plan_context(current_plan) if current_plan else {"items": []}

        return {
            "plan_date": plan_date,
            "trigger_source": trigger_source,
            "context_window_type": context_window_type,
            "language": language,
            "current_date": datetime.now(UTC).isoformat(),
            "user_profile": profile,
            "timezone": profile["timezone"],
            "preferences": preferences,
            "work_start_time": preferences["work_start_time"],
            "work_end_time": preferences["work_end_time"],
            "lunch_start_time": preferences["lunch_start_time"],
            "lunch_end_time": preferences["lunch_end_time"],
            "day_offs": preferences["day_offs"],
            "focus_hours": preferences["focus_hours"],
            "tasks": [self._task_context(task) for task in tasks],
            "current_schedule": current_schedule,
            "recent_feedback": feedback_list,
            "recent_activity": events_list,
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
            "preferences": self._preferences_payload(preference),
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
            "timezone": preference.user.timezone if preference.user else "Asia/Saigon",
            "work_start_time": preference.work_start_time,
            "work_end_time": preference.work_end_time,
            "lunch_start_time": preference.lunch_start_time,
            "lunch_end_time": preference.lunch_end_time,
            "day_offs": preference.day_offs,
            "focus_hours": preference.focus_hours,
        }

    @staticmethod
    def _time_str_to_mins(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
