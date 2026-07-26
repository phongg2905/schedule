"""
Generate synthetic dataset with positive labels for ML training.
===============================================================

Creates a realistic backlog scenario where:
  - Tasks are created on different days (not all same day as plan)
  - Some tasks are pre-assigned to D+1 plan → label=1
  - Other tasks remain in backlog → label=0
  - Activity events exist (completions, skips)
  - Various priorities, deadlines, task types

Usage:
    python scripts/generate_synthetic_dataset.py
        [--output data/synthetic_training_dataset.parquet]
        [--seed 42]

Output:
    - parquet dataset with positive labels (target ~5-10% positive)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from src.core.config import get_settings
get_settings.cache_clear()

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

from scripts.build_ml_dataset import build_dataset

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYNTH_START = date(2026, 7, 1)       # First task creation date
SYNTH_END = date(2026, 7, 24)        # Last plan date
SNAPSHOT_START = date(2026, 7, 10)   # First snapshot
SNAPSHOT_END = date(2026, 7, 23)     # Last snapshot (target = D+1)

USER_EMAIL = "synthetic-ml@example.com"
USER_TZ = "Asia/Saigon"

TASKS_PER_DAY_NEW = 5        # New routine tasks per day
TASKS_PER_DAY_BACKLOG = 8    # Backlog tasks per day
PREPLANNED_FRACTION = 0.50   # Fraction of backlog pre-planned for tomorrow

PRIORITY_DIST = {"urgent": 0.05, "high": 0.25, "normal": 0.50, "low": 0.20}
TYPE_DIST = {"scheduled": 0.70, "flexible": 0.30}

OUTPUT_DIR = BACKEND_ROOT / "data"
DEFAULT_OUTPUT = OUTPUT_DIR / "synthetic_training_dataset.parquet"


# ---------------------------------------------------------------------------
# RNG-based generators (all deterministic via seed)
# ---------------------------------------------------------------------------


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _random_priority(rng: np.random.Generator) -> str:
    return rng.choice(
        list(PRIORITY_DIST.keys()), p=list(PRIORITY_DIST.values())
    )


def _random_task_type(rng: np.random.Generator) -> str:
    return rng.choice(
        list(TYPE_DIST.keys()), p=list(TYPE_DIST.values())
    )


def _random_deadline(
    rng: np.random.Generator, snapshot_day: date
) -> str | None:
    """Generate a realistic deadline. 60% with deadline, 40% without."""
    if rng.random() < 0.40:
        return None
    choice = rng.random()
    if choice < 0.25:
        offset = int(rng.integers(-10, -1))
    elif choice < 0.50:
        offset = int(rng.integers(0, 2))
    elif choice < 0.80:
        offset = int(rng.integers(2, 14))
    else:
        offset = int(rng.integers(14, 60))
    d = snapshot_day + timedelta(days=offset)
    return d.isoformat()


def _random_tags(rng: np.random.Generator) -> list[str]:
    pool = ["work", "personal", "urgent", "health", "learning",
            "finance", "social", "admin"]
    n = int(rng.integers(0, 4))
    return sorted(rng.choice(pool, size=n, replace=False).tolist())


SCHEDULED_TITLES = [
    "Complete project report", "Team standup meeting",
    "Code review PR #42", "Update documentation",
    "Client presentation prep", "Database migration",
    "Write unit tests", "Deploy to staging",
    "Performance review prep", "Sprint planning",
    "One-on-one with manager", "Fix login bug",
    "API integration testing", "Security audit review",
    "Quarterly planning meeting",
]
FLEXIBLE_TITLES = [
    "Read technical article", "Exercise - morning jog",
    "Practice piano", "Learn Rust basics",
    "Meditate 15 min", "Organize desk",
    "Call mom", "Pay electricity bill",
    "Plan weekend trip", "Review budget",
    "Update resume", "Read book chapter",
    "Fix bike tire", "Meal prep for week",
    "Organize photo album",
]


def _random_title(rng: np.random.Generator, task_type: str) -> str:
    pool = SCHEDULED_TITLES if task_type == "scheduled" else FLEXIBLE_TITLES
    return str(rng.choice(pool))


def _random_description(rng: np.random.Generator, title: str) -> str:
    descs = [
        f"Need to finish {title.lower()} before end of week.",
        f"Follow up on {title.lower()} with the team.",
        f"Important: {title.lower()} needs attention today.",
        f"Schedule time for {title.lower()} in the afternoon.",
        f"Review and complete {title.lower()} as soon as possible.",
    ]
    return str(rng.choice(descs))


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------


def generate_synthetic_data(
    db: Session, *, seed: int = 42
) -> str:
    """Generate synthetic data with positive labels.

    Returns: user_id of the generated user.
    """
    rng = _rng(seed)

    # --- Create user ---
    uid = new_id()
    db.add(User(
        id=uid, email=USER_EMAIL, password_hash="synthetic",
        name="Synthetic ML User", timezone=USER_TZ, role="user",
    ))
    db.add(UserSchedulePreference(
        id=new_id(), user_id=uid,
        work_start_time="09:00", work_end_time="17:00",
        lunch_start_time="12:00", lunch_end_time="13:00",
        day_offs=["Saturday", "Sunday"], focus_hours=[],
    ))
    db.flush()
    print(f"  Created user: {uid}")

    # --- Build date range ---
    plan_dates: list[date] = []
    d = SYNTH_START
    while d <= SYNTH_END:
        plan_dates.append(d)
        d += timedelta(days=1)
    print(f"  Date range: {SYNTH_START} to {SYNTH_END} ({len(plan_dates)} days)")

    plan_ids: dict[date, str] = {}  # plan_date → plan_id
    all_task_ids: list[str] = []
    preplanned_new_task_ids: list[tuple[str, date]] = []  # (task_id, plan_day) for PASS 1b

    # ======================================================================
    # PASS 1: Create daily plans + new tasks + schedule items
    # ======================================================================
    for plan_day in plan_dates:
        plan_date_str = plan_day.isoformat()
        tomorrow = plan_day + timedelta(days=1)

        # --- Plan for today (D) ---
        snap = ContextSnapshot(
            id=new_id(), user_id=uid, snapshot_type="synthetic",
            context_payload={"plan_date": plan_date_str, "source": "synthetic_ml"},
        )
        plan = DailyPlan(
            id=new_id(), user_id=uid, plan_date=plan_date_str,
            status="confirmed", source="synthetic",
            context_snapshot_id=snap.id,
            explanation=f"Synthetic plan for {plan_date_str}",
        )
        schedule = Schedule(
            id=new_id(), user_id=uid, daily_plan_id=plan.id,
            schedule_date=plan_date_str, schedule_type="day",
            source="synthetic",
        )
        db.add_all([snap, plan, schedule])
        plan_ids[plan_day] = plan.id
        db.flush()  # materialize plan/schedule before referencing in tasks

        # --- New tasks for today ---
        for t in range(TASKS_PER_DAY_NEW):
            tid = new_id()
            ttype = _random_task_type(rng)
            created_ts = datetime(
                plan_day.year, plan_day.month, plan_day.day,
                0, 0, 0, tzinfo=UTC,
            )

            # First task: pre-planned for TOMORROW (D+1) → label=1 at snapshot D
            # Remaining: assigned to today's plan (D) → label=0
            is_preplanned = (t == 0 and tomorrow <= SYNTH_END)
            if is_preplanned:
                # Tomorrow's plan might not be created yet in PASS 1.
                # Use a plan_date-based lookup instead.
                task_daily_plan_id = None  # will be set in PASS 2 after all plans exist
            else:
                task_daily_plan_id = plan.id

            task = Task(
                id=tid, user_id=uid,
                daily_plan_id=task_daily_plan_id,
                title=_random_title(rng, ttype),
                description=_random_description(rng, ttype),
                estimated_duration=int(rng.integers(15, 120)),
                deadline=_random_deadline(rng, plan_day),
                start_time=None, task_type=ttype,
                priority=_random_priority(rng), status="planned",
                tags=_random_tags(rng), completed_at=None,
                created_at=created_ts, updated_at=created_ts,
            )
            db.add(task)
            all_task_ids.append(tid)

            # Schedule item (only for TODAY's tasks, not pre-planned ones)
            if not is_preplanned:
                db.flush()  # ensure task exists before schedule item
                db.add(ScheduleItem(
                    id=new_id(), schedule_id=schedule.id, task_id=tid,
                    start_time=f"{8 + t:02d}:00",
                    end_time=f"{9 + t:02d}:00",
                    label=task.title, status="planned",
                    source="synthetic",
                ))

            # Track pre-planned task IDs for PASS 1b (update daily_plan_id)
            if is_preplanned:
                preplanned_new_task_ids.append((tid, plan_day))

    db.flush()
    print(f"  PASS 1 done: {len(plan_ids)} plans, tasks created")

    # ======================================================================
    # PASS 1b: Update pre-planned tasks to reference tomorrow's plan
    # Now all plans from PASS 1 exist, so FK references will work.
    # ======================================================================
    for tid, plan_day in preplanned_new_task_ids:
        tomorrow = plan_day + timedelta(days=1)
        if tomorrow > SYNTH_END:
            continue
        if tomorrow not in plan_ids:
            continue
        tomorrow_plan_id = plan_ids[tomorrow]
        db.execute(
            text("UPDATE tasks SET daily_plan_id = :pid WHERE id = :tid"),
            {"pid": tomorrow_plan_id, "tid": tid},
        )

    db.flush()
    print(f"  PASS 1b done: {len(preplanned_new_task_ids)} tasks linked to tomorrow's plans")

    # ======================================================================
    # PASS 2: Create backlog tasks + pre-planned-for-tomorrow tasks
    # ======================================================================
    preplanned_count = 0
    for plan_day in plan_dates:
        tomorrow = plan_day + timedelta(days=1)
        if tomorrow > SYNTH_END:
            break
        if tomorrow not in plan_ids:
            continue

        tomorrow_plan_id = plan_ids[tomorrow]

        for _ in range(TASKS_PER_DAY_BACKLOG):
            tid = new_id()
            ttype = _random_task_type(rng)

            # Creation date: a few days before plan_day (backlog)
            created_offset = int(rng.integers(2, 8))
            created_date = plan_day - timedelta(days=created_offset)
            if created_date < SYNTH_START:
                created_date = SYNTH_START
            created_ts = datetime(
                created_date.year, created_date.month, created_date.day,
                0, 0, 0, tzinfo=UTC,
            )

            planned_for_tomorrow = rng.random() < PREPLANNED_FRACTION
            task_daily_plan_id = tomorrow_plan_id if planned_for_tomorrow else None
            if planned_for_tomorrow:
                preplanned_count += 1

            task = Task(
                id=tid, user_id=uid,
                daily_plan_id=task_daily_plan_id,
                title=_random_title(rng, ttype),
                description=_random_description(rng, ttype),
                estimated_duration=int(rng.integers(15, 120)),
                deadline=_random_deadline(rng, created_date),
                start_time=None, task_type=ttype,
                priority=_random_priority(rng), status="todo",
                tags=_random_tags(rng), completed_at=None,
                created_at=created_ts, updated_at=created_ts,
            )
            db.add(task)
            all_task_ids.append(tid)

    db.flush()
    print(f"  PASS 2 done: backlog tasks created, {preplanned_count} pre-planned for tomorrow")

    # ======================================================================
    # Activity events
    # ======================================================================
    event_count = 0
    for tid in all_task_ids:
        if rng.random() < 0.15:  # task_completed
            event_count += 1
            event_day = SYNTH_START + timedelta(
                days=int(rng.integers(2, (SYNTH_END - SYNTH_START).days - 2))
            )
            db.add(ActivityEvent(
                id=new_id(), user_id=uid, event_type="task_completed",
                entity_type="task", entity_id=tid, source="manual",
                payload={},
                occurred_at=datetime(
                    event_day.year, event_day.month, event_day.day,
                    10, 0, 0, tzinfo=UTC,
                ),
            ))
        elif rng.random() < 0.08:  # task_skipped (conditional prob ~= 8%)
            event_count += 1
            event_day = SYNTH_START + timedelta(
                days=int(rng.integers(2, (SYNTH_END - SYNTH_START).days - 2))
            )
            db.add(ActivityEvent(
                id=new_id(), user_id=uid, event_type="task_skipped",
                entity_type="task", entity_id=tid, source="manual",
                payload={},
                occurred_at=datetime(
                    event_day.year, event_day.month, event_day.day,
                    10, 0, 0, tzinfo=UTC,
                ),
            ))
        elif rng.random() < 0.12:  # task_delayed
            event_count += 1
            event_day = SYNTH_START + timedelta(
                days=int(rng.integers(2, (SYNTH_END - SYNTH_START).days - 2))
            )
            db.add(ActivityEvent(
                id=new_id(), user_id=uid, event_type="task_delayed",
                entity_type="task", entity_id=tid, source="manual",
                payload={},
                occurred_at=datetime(
                    event_day.year, event_day.month, event_day.day,
                    10, 0, 0, tzinfo=UTC,
                ),
            ))

    # --- Day summaries ---
    for plan_day in plan_dates:
        summary_payload = {
            "summary_date": plan_day.isoformat(),
            "total_tasks": TASKS_PER_DAY_NEW + TASKS_PER_DAY_BACKLOG,
            "source": "synthetic_ml",
        }
        db.add(DaySummary(
            id=new_id(), user_id=uid,
            summary_date=plan_day.isoformat(),
            summary_payload=summary_payload,
        ))

    # --- Commit ---
    db.commit()

    # --- Stats ---
    total_tasks = db.execute(
        text("SELECT COUNT(*) FROM tasks WHERE user_id = :uid"), {"uid": uid}
    ).scalar()
    total_plans = db.execute(
        text("SELECT COUNT(*) FROM daily_plans WHERE user_id = :uid"), {"uid": uid}
    ).scalar()
    total_events = db.execute(
        text("SELECT COUNT(*) FROM activity_events WHERE user_id = :uid"), {"uid": uid}
    ).scalar()
    num_preplanned = db.execute(
        text("SELECT COUNT(*) FROM tasks t "
             "JOIN daily_plans dp ON dp.id = t.daily_plan_id "
             "WHERE t.user_id = :uid AND t.daily_plan_id IS NOT NULL"),
        {"uid": uid},
    ).scalar()

    print(f"\n=== Generation Stats ===")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Total plans: {total_plans}")
    print(f"  Total activity events: {total_events}")
    print(f"  Tasks with daily_plan_id: {num_preplanned}")

    return uid


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate synthetic ML training dataset with positive labels"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output parquet file path",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args(argv)

    # --- Setup in-memory SQLite ---
    print("=== Synthetic Dataset Generator ===")
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # --- Generate data ---
        t0 = time.time()
        uid = generate_synthetic_data(db, seed=args.seed)
        gen_time = time.time() - t0

        # --- Build dataset ---
        print(f"\n=== Building dataset ===")
        t0 = time.time()
        df = build_dataset(
            db, SNAPSHOT_START, SNAPSHOT_END,
            user_id=uid, min_history_days=0,
        )
        build_time = time.time() - t0

        if df.empty:
            print("ERROR: No training rows generated!")
            return 1

        # --- Determine output path ---
        if args.output:
            output_path = Path(args.output)
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DEFAULT_OUTPUT

        # --- Write parquet ---
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_for_export = df.drop(columns=["task_title_hint"], errors="ignore")
        df_for_export.to_parquet(
            str(output_path), index=False, compression="zstd",
        )

        file_size_kb = output_path.stat().st_size / 1024
        pos = int(df["label"].sum())
        neg = len(df) - pos
        total = len(df)
        pos_pct = pos / total * 100 if total else 0

        print(f"\n{'=' * 60}")
        print(f"DATASET: {output_path} ({file_size_kb:.1f} KB)")
        print(f"{'=' * 60}")
        print(f"  Total rows: {total:,}")
        print(f"  Positive labels: {pos:,} ({pos_pct:.1f}%)")
        print(f"  Negative labels: {neg:,} ({neg:.1f}%)")
        print(f"  Imbalance ratio: {neg/max(pos,1):.1f}:1")
        print(f"  Snapshot range: {SNAPSHOT_START} to {SNAPSHOT_END}")
        print(f"  Build time: {build_time:.2f}s")
        print(f"  Total time: {gen_time + build_time:.2f}s")
        print(f"{'=' * 60}")
        print(f"\nNext step:")
        print(f"  python scripts/train_baseline.py --dataset {output_path}")
        print(f"  python scripts/rule_baseline.py --dataset {output_path}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
