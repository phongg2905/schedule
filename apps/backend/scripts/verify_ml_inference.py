"""
Verify ML Inference End-to-End
================================

Creates test data, calls DailyPlanService.draft() for tomorrow's plan,
and prints the ML scores and plan details to stdout.

Usage:
    python scripts/verify_ml_inference.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
get_settings.cache_clear()

from src.db.base import Base
from src.db.models import ActivityEvent, ContextSnapshot, Task, User, UserSchedulePreference, new_id
from src.modules.daily_plans.service import DailyPlanService
from src.modules.ml.prediction_service import MLPredictionService

SEP = "=" * 70


def create_user_with_data(session: Session) -> tuple[str, list[str], date]:
    """Create test user with diverse tasks. Returns (user_id, task_ids, plan_date)."""
    today = date.today()
    plan_date = today + timedelta(days=1)
    while plan_date.weekday() >= 5:
        plan_date += timedelta(days=1)

    uid = new_id()
    session.add(User(
        id=uid, email="verify-ml@example.com",
        password_hash="fakehash", name="Verify ML User",
        timezone="Asia/Saigon", role="user",
    ))
    session.add(UserSchedulePreference(
        id=new_id(), user_id=uid,
        work_start_time="09:00", work_end_time="17:00",
        lunch_start_time="12:00", lunch_end_time="13:00",
        day_offs=["Saturday", "Sunday"], focus_hours=[],
    ))
    session.flush()

    task_configs = [
        ("Overdue deadline task",  "urgent", "scheduled", -1, True,  ["work"],      5),
        ("Urgent today deadline",  "urgent", "scheduled",  0, True,  ["critical"],  4),
        ("High priority task",     "high",   "scheduled",  3, True,  ["work"],      3),
        ("Normal routine task",    "normal", "scheduled",  7, True,  [],            2),
        ("Flexible personal task", "normal", "flexible",   14, False, ["personal"],  1),
        ("Low priority backlog",   "low",    "scheduled",  30, False, [],            0),
    ]

    task_ids = []
    for title, priority, task_type, deadline_offset, has_desc, tags, created_offset in task_configs:
        tid = new_id()
        deadline = (today + timedelta(days=deadline_offset)).isoformat() if deadline_offset is not None else None
        desc = f"Description: {title}" if has_desc else None
        created = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=UTC) - timedelta(days=created_offset)
        session.add(Task(
            id=tid, user_id=uid, title=title, description=desc,
            estimated_duration=60, deadline=deadline,
            task_type=task_type, priority=priority, status="todo",
            tags=tags, created_at=created, updated_at=created,
        ))
        task_ids.append(tid)

    for i, tid in enumerate(task_ids[:3]):
        session.add(ActivityEvent(
            id=new_id(), user_id=uid, event_type="task_completed",
            entity_type="task", entity_id=tid, source="manual",
            payload={},
            occurred_at=datetime(today.year, today.month, today.day, 10, 0, 0, tzinfo=UTC) - timedelta(days=1 + i),
        ))

    session.add(ActivityEvent(
        id=new_id(), user_id=uid, event_type="task_delayed",
        entity_type="task", entity_id=task_ids[4], source="manual",
        payload={},
        occurred_at=datetime(today.year, today.month, today.day, 10, 0, 0, tzinfo=UTC) - timedelta(days=1),
    ))

    session.commit()
    return uid, task_ids, plan_date


def main() -> int:
    t_start = time.time()

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print(SEP)
        print("  VERIFY ML INFERENCE - END-TO-END")
        print(SEP)

        print("\n[1/4] Creating test data...")
        uid, task_ids, plan_date = create_user_with_data(db)
        print(f"  User ID:     {uid[:8]}...")
        print(f"  Tasks:       {len(task_ids)} created")
        print(f"  Plan date:   {plan_date} ({plan_date.strftime('%A')})")

        print("\n[2/4] Generating daily plan draft...")
        service = DailyPlanService(db, uid)
        plan = service.draft(
            plan_date=plan_date.isoformat(),
            context_window_type="verify_ml",
            trigger_source="manual",
        )
        print(f"  Plan ID:     {plan.id[:8]}...")
        print(f"  Plan source: {plan.source}")
        print(f"  Plan status: {plan.status}")
        print(f"  Explanation: {plan.explanation}")

        print("\n[3/4] Checking context_snapshot ML metadata...")
        snapshot = db.get(ContextSnapshot, plan.context_snapshot_id)
        if snapshot is None:
            print("  FAIL - No context snapshot found!")
            return 1

        payload = snapshot.context_payload
        if "ml" not in payload:
            print("  FAIL - No ML metadata in context snapshot!")
            print(f"  Available keys: {list(payload.keys())}")
            return 1

        ml_data = payload["ml"]
        print(f"  ML status:   {ml_data.get('status', '?')}")
        print(f"  Classifier:  {ml_data.get('classifier', '?')}")
        print(f"  Scored:      {ml_data.get('n_scored', '?')}/{ml_data.get('n_candidates', '?')} tasks")
        print(f"  High conf:   {ml_data.get('n_high_confidence', '?')}")
        print(f"  Medium conf: {ml_data.get('n_medium_confidence', '?')}")
        print(f"  Fallback:    {ml_data.get('fallback_used', '?')}")

        print(f"\n[4/4] ML Scores per task:")
        print(f"  {'Task':35s} {'Score':>8s} {'Band':>8s} {'Scheduled?':>10s}")
        print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*10}")

        scheduled_ids = set()
        for schedule in plan.schedules:
            for item in schedule.items:
                if item.task_id:
                    scheduled_ids.add(item.task_id)

        ml_service = MLPredictionService()
        result = ml_service.predict_result(
            [db.get(Task, tid) for tid in task_ids],
            db, uid,
            snapshot_date=plan_date - timedelta(days=1),
            timezone_str="Asia/Saigon",
        )

        if result and result.predictions:
            for pred in sorted(result.predictions, key=lambda p: -p.score):
                task = db.get(Task, pred.task_id)
                title = task.title[:34] if task else pred.task_id[:8]
                scheduled = "[x]" if pred.task_id in scheduled_ids else "[ ]"
                print(f"  {title:35s} {pred.score:8.4f} {pred.confidence_band:>8s} {scheduled:>10s}")
        else:
            print("  FAIL - Could not retrieve ML scores")
            return 1

        elapsed = time.time() - t_start
        print(f"\n{SEP}")
        if result and not result.fallback_used:
            print(f"  PASS - ML INFERENCE VERIFIED ({elapsed:.2f}s)")
            print(f"  {result.n_scored} tasks scored by {result.classifier_type}")
            print(f"  Plan source: '{plan.source}'")
        else:
            print(f"  WARN - ML fallback used ({elapsed:.2f}s)")
            if result:
                print(f"  Status: {result.result_status}")
        print(SEP)
        return 0

    except Exception as e:
        print(f"\nFAIL: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
