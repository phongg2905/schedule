"""
Performance benchmark for build_ml_dataset.py.

Measures:
  - Total build time (batch version, current)
  - Time per component (candidates, status batch, event counts, user context)
  - Theoretical per-task query cost vs actual batch query cost

Usage:
    python scripts/benchmark_ml_dataset.py
    python scripts/benchmark_ml_dataset.py --user-id <uuid>  # run against a specific user
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Use the reseeded data if available, otherwise fall back to in-memory
import argparse

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
from src.db.base import Base
from src.db.models import (
    ActivityEvent,
    ContextSnapshot,
    DailyPlan,
    DaySummary,
    Schedule,
    ScheduleItem,
    Task,
    User,
    UserSchedulePreference,
    new_id,
)
from src.db.session import get_session_factory

from scripts.build_ml_dataset import (
    _batch_get_event_counts,
    _batch_reconstruct_statuses,
    _build_rows_for_snapshot,
    _get_candidate_tasks,
    _get_plan_for_date,
    _get_preferences,
    _get_user_context_features,
    build_dataset,
    compute_end_of_day,
)


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _timed(name: str, fn, **kwargs) -> Any:
    """Run a function, print timing, return (result, elapsed_seconds)."""
    t0 = time.perf_counter()
    result = fn(**kwargs)
    elapsed = time.perf_counter() - t0
    print(f"    {name:35s} {elapsed:8.3f}s")
    return result, elapsed


# ---------------------------------------------------------------------------
# In-memory dataset builder (used if no user specified)
# ---------------------------------------------------------------------------


def build_in_memory_dataset() -> tuple[Session, str, int, int, int]:
    """Create a realistic test dataset in-memory: 1 user, 29 days, 696 tasks, 29 plans."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    uid = new_id()
    PLAN_START = date(2026, 7, 6)
    PLAN_END = date(2026, 8, 3)

    # Create user + preferences
    db.add(User(id=uid, email="bench@test.com", password_hash="fake",
                name="Benchmark", timezone="Asia/Saigon", role="user"))
    db.add(UserSchedulePreference(id=new_id(), user_id=uid,
        work_start_time="09:00", work_end_time="17:00",
        lunch_start_time="12:00", lunch_end_time="13:00",
        day_offs=["Saturday", "Sunday"], focus_hours=[]))
    db.commit()

    total_tasks = 0
    total_plans = 0

    current_day = PLAN_START
    while current_day <= PLAN_END:
        date_str = current_day.isoformat()
        creation_ts = datetime(current_day.year, current_day.month, current_day.day, 0, 0, 0, tzinfo=UTC)

        snap = ContextSnapshot(id=new_id(), user_id=uid, snapshot_type="bench",
                               context_payload={}, created_at=creation_ts, updated_at=creation_ts)
        plan = DailyPlan(id=new_id(), user_id=uid, plan_date=date_str, status="confirmed",
                         source="bench", explanation="Bench plan", context_snapshot_id=snap.id,
                         created_at=creation_ts, updated_at=creation_ts)
        schedule = Schedule(id=new_id(), user_id=uid, daily_plan_id=plan.id,
                            schedule_date=date_str, schedule_type="day", source="bench",
                            created_at=creation_ts, updated_at=creation_ts)
        db.add_all([snap, plan, schedule])
        total_plans += 1

        # 24 tasks per day (same as reseed script)
        for i in range(24):
            task = Task(id=new_id(), user_id=uid, daily_plan_id=plan.id,
                title=f"Task {current_day} #{i}", deadline=date_str,
                estimated_duration=60, priority="normal", task_type="scheduled",
                status="planned", tags=[], completed_at=None,
                created_at=creation_ts, updated_at=creation_ts)
            item = ScheduleItem(id=new_id(), schedule_id=schedule.id, task_id=task.id,
                start_time=f"{i:02d}:00:00", end_time=f"{(i+1)%24:02d}:00:00",
                label=task.title, status="planned", source="bench",
                created_at=creation_ts, updated_at=creation_ts)
            db.add_all([task, item])
            total_tasks += 1

        day_summary = DaySummary(id=new_id(), user_id=uid, summary_date=date_str,
            summary_payload={}, created_at=creation_ts, updated_at=creation_ts)
        db.add(day_summary)

        db.add(ActivityEvent(id=new_id(), user_id=uid, event_type="daily_plan_created",
            entity_type="daily_plan", entity_id=plan.id, source="system",
            payload={}, occurred_at=creation_ts))

        current_day += __import__("datetime").timedelta(days=1)

    db.commit()

    # Count schedule_items and events
    item_count = db.execute(text("SELECT COUNT(*) FROM schedule_items WHERE schedule_id IN (SELECT id FROM schedules WHERE user_id=:uid)"), {"uid": uid}).scalar()
    event_count = db.execute(text("SELECT COUNT(*) FROM activity_events WHERE user_id=:uid"), {"uid": uid}).scalar()

    print(f"\n  Dataset built: {total_tasks} tasks, {total_plans} plans, {item_count} schedule_items, {event_count} events")
    return db, uid, total_tasks, total_plans, event_count


# ---------------------------------------------------------------------------
# Component profiling
# ---------------------------------------------------------------------------


def profile_single_snapshot(db: Session, user_id: str, snapshot_date: date):
    """Profile each component of a single snapshot build."""
    prefs = _get_preferences(db, user_id)
    end_of_d = compute_end_of_day(snapshot_date, "Asia/Saigon")
    target_date = snapshot_date + __import__("datetime").timedelta(days=1)

    print(f"\n  Snapshot D={snapshot_date}, target={target_date}")

    # 1. Candidate tasks
    candidates, t_cand = _timed("_get_candidate_tasks", _get_candidate_tasks,
                                 db=db, user_id=user_id, end_of_d=end_of_d)
    n = len(candidates)
    task_ids = [t["id"] for t in candidates]

    # 2. Batch status reconstruction
    _, t_status = _timed("_batch_reconstruct_statuses", _batch_reconstruct_statuses,
                          db=db, user_id=user_id, task_ids=task_ids, end_of_d=end_of_d)

    # 3. Batch event counts
    _, t_events = _timed("_batch_get_event_counts", _batch_get_event_counts,
                          db=db, user_id=user_id, task_ids=task_ids, end_of_d=end_of_d)

    # 4. User context
    _, t_context = _timed("_get_user_context_features", _get_user_context_features,
                           db=db, user_id=user_id, end_of_d=end_of_d,
                           timezone_str="Asia/Saigon", target_date=target_date,
                           snapshot_date=snapshot_date)

    # 5. Plan lookup
    _, t_plan = _timed("_get_plan_for_date", _get_plan_for_date,
                        db=db, user_id=user_id, target_date=target_date)

    # 6. Full snapshot
    _, t_full = _timed("_build_rows_for_snapshot", _build_rows_for_snapshot,
                        db=db, user_id=user_id, snapshot_date=snapshot_date, prefs=prefs)

    # Estimated per-task query cost
    total_time = t_cand + t_status + t_events + t_context + t_plan
    print(f"  Total component time: {total_time:.3f}s for {n} candidate tasks")

    return {
        "candidates": n,
        "time_candidates": t_cand,
        "time_status_batch": t_status,
        "time_events_batch": t_events,
        "time_context": t_context,
        "time_plan": t_plan,
        "time_full": t_full,
        "total_component_time": total_time,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark ML dataset build")
    parser.add_argument("--user-id", type=str, default=None, help="Existing user ID to benchmark")
    parser.add_argument("--from-date", type=str, default="2026-07-07", help="Snapshot start date")
    parser.add_argument("--to-date", type=str, default="2026-08-02", help="Snapshot end date")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("ML DATASET BUILD - PERFORMANCE BENCHMARK")
    print("=" * 70)

    if args.user_id:
        print(f"\nUsing existing user: {args.user_id}")
        print(f"Connecting to database...")
        settings = get_settings()
        session_factory = get_session_factory()
        db = session_factory()
        uid = args.user_id
        from_date = __import__("datetime").date.fromisoformat(args.from_date)
        to_date = __import__("datetime").date.fromisoformat(args.to_date)

        # Count existing data
        task_count = db.execute(text("SELECT COUNT(*) FROM tasks WHERE user_id=:uid"), {"uid": uid}).scalar()
        plan_count = db.execute(text("SELECT COUNT(*) FROM daily_plans WHERE user_id=:uid"), {"uid": uid}).scalar()
        print(f"  Existing data: {task_count} tasks, {plan_count} plans")
    else:
        print(f"\nBuilding in-memory dataset...")
        t0 = time.perf_counter()
        db, uid, task_count, plan_count, event_count = build_in_memory_dataset()
        build_time = time.perf_counter() - t0
        print(f"  Dataset build: {build_time:.2f}s")
        from_date = date(2026, 7, 10)  # Use smaller range for in-memory to save time
        to_date = date(2026, 7, 15)

    try:
        num_dates = (to_date - from_date).days + 1

        # ------------------------------------------------------------------
        # BENCHMARK 1: Profile a single mid-range snapshot
        # ------------------------------------------------------------------
        print(f"\n{'=' * 70}")
        print(f"BENCHMARK 1: Single Snapshot Profile (D={from_date + __import__('datetime').timedelta(days=num_dates//2)})")
        print(f"{'=' * 70}")
        mid_date = from_date + __import__("datetime").timedelta(days=num_dates // 2)
        profile = profile_single_snapshot(db, uid, mid_date)
        n_candidates = profile["candidates"]

        # ------------------------------------------------------------------
        # BENCHMARK 2: Full build time
        # ------------------------------------------------------------------
        print(f"\n{'=' * 70}")
        print(f"BENCHMARK 2: Full Dataset Build ({num_dates} snapshot days)")
        print(f"{'=' * 70}")
        t0 = time.perf_counter()
        df = build_dataset(db, from_date, to_date, user_id=uid, min_history_days=0)
        total_time = time.perf_counter() - t0
        total_rows = len(df)
        print(f"\n  Total time: {total_time:.2f}s for {total_rows} rows")
        print(f"  Throughput: {total_rows / total_time:.0f} rows/s")

        # ------------------------------------------------------------------
        # ANALYSIS: Batch vs Per-Task comparison
        # ------------------------------------------------------------------
        print(f"\n{'=' * 70}")
        print(f"ANALYSIS: Batch Queries vs Per-Task Queries")
        print(f"{'=' * 70}")

        # Current batch approach: queries per snapshot
        batch_queries_per_snapshot = {
            "candidate_tasks": 1,
            "batch_status": 1,
            "batch_events": 1,
            "user_context (multiple)": 6,  # 6 individual queries in _get_user_context_features
            "plan_lookup": 1,
            "label_per_task": 0,  # cached at snapshot level, no extra query
        }
        total_batch_snapshot_queries = sum(batch_queries_per_snapshot.values())

        # Per-task approach: queries per snapshot
        per_task_queries_per_snapshot = {
            "candidate_tasks": 1,
            "status_per_task": n_candidates,  # 1 query per task
            "events_per_task": n_candidates,  # 1 query per task
            "user_context (multiple)": 6,
            "plan_lookup": 1,
            "label_per_task": 1,  # 1 extra query per task (if not cached)
        }
        total_per_task_snapshot_queries = sum(per_task_queries_per_snapshot.values())

        print(f"\n  Per snapshot (with ~{n_candidates} candidate tasks):")
        print(f"  {'Metric':50s} {'Batch':>10s} {'Per-Task':>10s} {'Ratio':>10s}")
        print(f"  {'-' * 82}")
        print(f"  {'Query count':50s} {total_batch_snapshot_queries:>10d} {total_per_task_snapshot_queries:>10d} "
              f"{total_per_task_snapshot_queries/max(total_batch_snapshot_queries,1):>10.0f}x")

        total_batch_all = total_batch_snapshot_queries * num_dates
        total_per_task_all = total_per_task_snapshot_queries * num_dates
        print(f"  {'Query count (all ' + str(num_dates) + ' snapshots)':50s} {total_batch_all:>10d} {total_per_task_all:>10d} "
              f"{total_per_task_all/max(total_batch_all,1):>10.0f}x")

        print(f"\n  Time savings:")
        print(f"  {'Batch total time':50s} {total_time:>10.2f}s")
        # Estimate per-task time: query overhead dominates
        per_task_est = n_candidates * num_dates * 0.001 * 2  # 1ms per extra query, 2 extra per task
        print(f"  {'Estimated per-task overhead (1ms/extra query)':50s} ~{per_task_est:.1f}s extra")
        print(f"  {'Estimated per-task total':50s} ~{total_time + per_task_est:.1f}s")

        # ------------------------------------------------------------------
        # Component time breakdown
        # ------------------------------------------------------------------
        print(f"\n{'=' * 70}")
        print(f"COMPONENT TIME BREAKDOWN (single snapshot)")
        print(f"{'=' * 70}")
        component_times = [
            ("_get_candidate_tasks (1 query)", profile["time_candidates"]),
            ("_batch_reconstruct_statuses (1 query)", profile["time_status_batch"]),
            ("_batch_get_event_counts (1 query)", profile["time_events_batch"]),
            ("_get_user_context_features (6 queries)", profile["time_context"]),
            ("_get_plan_for_date (1 query)", profile["time_plan"]),
        ]
        sorted_times = sorted(component_times, key=lambda x: x[1], reverse=True)
        total_comp = sum(t for _, t in component_times)
        print(f"  {'Component':50s} {'Time':>8s} {'%':>8s}")
        print(f"  {'-' * 68}")
        for name, t in sorted_times:
            pct = t / total_comp * 100 if total_comp > 0 else 0
            print(f"  {name:50s} {t:8.3f}s {pct:7.1f}%")
        print(f"  {'-' * 68}")
        print(f"  {'Total':50s} {total_comp:8.3f}s {100:7.1f}%")

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        print(f"\n{'=' * 70}")
        print(f"SUMMARY")
        print(f"{'=' * 70}")
        print(f"  Dataset: {task_count} tasks, {plan_count} plans, {num_dates} snapshots")
        print(f"  Total rows generated: {total_rows}")
        print(f"  Total build time: {total_time:.2f}s")
        print(f"  Avg time per snapshot: {total_time/num_dates:.3f}s")
        print(f"  Avg time per row: {total_time/max(total_rows,1)*1000:.1f}ms")
        print(f"  Query reduction (batch vs per-task): {total_per_task_all/max(total_batch_all,1):.0f}x")

        print(f"\n  {'=' * 70}")
        print(f"  BENCHMARK COMPLETE")
        print(f"  {'=' * 70}")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if not args.user_id:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
