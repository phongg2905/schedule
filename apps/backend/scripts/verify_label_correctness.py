"""
Verify label correctness for build_ml_dataset.py.

Scenario:
  - Snapshot date D = 2026-07-15
  - 5 tasks created before D with different deadlines
  - Daily plan for D+1 = 2026-07-16, confirms 2 tasks (with daily_plan_id set)
  - Expected labels: [1, 1, 0, 0, 0]

Usage:
    python scripts/verify_label_correctness.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

# Ensure backend src is on path
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
from src.db.models import (
    ContextSnapshot,
    DailyPlan,
    Task,
    User,
    UserSchedulePreference,
    new_id,
)
from src.db.session import get_session_factory

from scripts.build_ml_dataset import (
    _build_rows_for_snapshot,
    _get_preferences,
    compute_end_of_day,
)


def _make_plan(session: Session, user_id: str, plan_date: str) -> DailyPlan:
    snap = ContextSnapshot(id=new_id(), user_id=user_id, snapshot_type="test", context_payload={})
    plan = DailyPlan(
        id=new_id(), user_id=user_id, plan_date=plan_date,
        status="confirmed", source="test",
        context_snapshot_id=snap.id, explanation="Test plan",
    )
    session.add_all([snap, plan])
    session.flush()
    return plan


def _make_task(
    session: Session, user_id: str, title: str, deadline: str,
    daily_plan_id: str | None = None,
) -> Task:
    task = Task(
        id=new_id(), user_id=user_id, title=title,
        deadline=deadline, estimated_duration=60,
        priority="normal", task_type="scheduled", status="todo",
        tags=[], completed_at=None,
        created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
        daily_plan_id=daily_plan_id,
    )
    session.add(task)
    session.flush()
    return task


def main() -> int:
    # --- Setup: in-memory SQLite ---
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # --- Create user ---
        uid = new_id()
        db.add(User(
            id=uid, email="verify@test.com", password_hash="fake",
            name="Verify", timezone="Asia/Saigon", role="user",
        ))
        db.add(UserSchedulePreference(
            id=new_id(), user_id=uid,
            work_start_time="09:00", work_end_time="17:00",
            lunch_start_time="12:00", lunch_end_time="13:00",
            day_offs=["Saturday", "Sunday"], focus_hours=[],
        ))
        db.commit()

        SNAPSHOT = date(2026, 7, 15)  # D
        TARGET = date(2026, 7, 16)    # D+1

        # --- Create plan for D+1 ---
        plan = _make_plan(db, uid, TARGET.isoformat())

        # --- Create 5 tasks ---
        # 2 tasks IN the plan (daily_plan_id = plan.id)
        tasks = [
            _make_task(db, uid, "Gap task A - in plan", "2026-07-16", daily_plan_id=plan.id),
            _make_task(db, uid, "Gap task B - in plan", "2026-07-17", daily_plan_id=plan.id),
            # 3 tasks NOT in plan (daily_plan_id = None)
            _make_task(db, uid, "Xa task C - not planned", "2026-08-01"),
            _make_task(db, uid, "Xa task D - not planned", "2026-08-10"),
            _make_task(db, uid, "Xa task E - not planned", "2026-09-01"),
        ]
        db.commit()

        # --- Run snapshot ---
        prefs = _get_preferences(db, uid)
        rows = _build_rows_for_snapshot(db, uid, SNAPSHOT, prefs)

        # --- Verify ---
        print("=" * 60)
        print("LABEL CORRECTNESS VERIFICATION")
        print("=" * 60)

        # Check we got all 5 tasks
        assert len(rows) == 5, f"Expected 5 rows, got {len(rows)}"
        print(f"\nTotal candidate tasks: {len(rows)}")

        # Build title → label mapping
        labels = {}
        for r in rows:
            labels[r["task_title_hint"]] = r["label"]

        print(f"\n{'Task':40s} {'Deadline':12s} {'Label':>6s}")
        print("-" * 60)
        for t in tasks:
            label = labels.get(t.title[:50], "???")
            print(f"{t.title[:40]:40s} {t.deadline:12s} {label:>6d}")

        # Expected labels: first 2 in plan = 1, last 3 not in plan = 0
        expected = [1, 1, 0, 0, 0]
        actual = [labels[t.title[:50]] for t in tasks]
        print(f"\nExpected labels: {expected}")
        print(f"Actual labels:   {actual}")
        assert actual == expected, f"MISMATCH: expected {expected}, got {actual}"
        print("\nPASS: Labels match expected values.")

        # Additional checks
        print(f"\nSnapshot date: {rows[0]['snapshot_date']}")
        print(f"Target date:   {rows[0]['target_date']}")
        print(f"All deadlines have has_deadline=True: {all(r['has_deadline'] for r in rows)}")

        # Task A and B should have earlier deadlines
        rows_by_title = {r["task_title_hint"]: r for r in rows}
        print(f"\nDeadline relative days (expected: positive = future):")
        for t in tasks:
            hint = t.title[:50]
            drd = rows_by_title[hint]["deadline_relative_days"]
            overdue = rows_by_title[hint]["is_overdue"]
            print(f"  {t.title[:30]:30s} deadline_relative_days={drd:3d} is_overdue={overdue}")

        print("\n" + "=" * 60)
        print("ALL CHECKS PASSED")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\nFAIL: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
