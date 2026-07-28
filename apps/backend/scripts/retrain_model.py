"""
Retrain Model — Rich In-Memory Seed + Training
================================================

Creates an in-memory SQLite database with:
  - 24 routine tasks per day (linked to TODAY's plan) — label=0
  - Backlog tasks per day (some pre-planned for TOMORROW's plan) — label=1
  - Activity events for realism

Then builds an ML dataset and trains a new model.

Usage:
    python scripts/retrain_model.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
get_settings.cache_clear()

from src.db.base import Base
from src.db.models import (
    ActivityEvent, ContextSnapshot, DailyPlan,
    Schedule, ScheduleItem, Task, User, UserSchedulePreference, new_id,
)
from scripts.build_ml_dataset import build_dataset
from scripts.train_baseline import train_pipeline

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

START_DATE = date(2026, 7, 1)
END_DATE = date(2026, 7, 28)
SNAPSHOT_START = date(2026, 7, 10)
SNAPSHOT_END = date(2026, 7, 27)

USER_EMAIL = "retrain-user@example.com"
USER_TZ = "Asia/Saigon"

ROUTINE_SLOTS: list[tuple[str, str, str, str]] = [
    ("00:00", "01:00", "Sleep", "low"), ("01:00", "02:00", "Sleep", "low"),
    ("02:00", "03:00", "Sleep", "low"), ("03:00", "04:00", "Sleep", "low"),
    ("04:00", "05:00", "Sleep", "low"), ("05:00", "06:00", "Wake up", "low"),
    ("06:00", "07:00", "Morning routine", "normal"), ("07:00", "08:00", "Breakfast", "normal"),
    ("08:00", "09:00", "Plan review", "normal"), ("09:00", "10:00", "Deep work", "high"),
    ("10:00", "11:00", "Deep work", "high"), ("11:00", "12:00", "Email", "high"),
    ("12:00", "13:00", "Lunch", "normal"), ("13:00", "14:00", "Deep work", "high"),
    ("14:00", "15:00", "Deep work", "high"), ("15:00", "16:00", "Team sync", "high"),
    ("16:00", "17:00", "Wrap up", "high"), ("17:00", "18:00", "Exercise", "normal"),
    ("18:00", "19:00", "Dinner", "normal"), ("19:00", "20:00", "Learning", "normal"),
    ("20:00", "21:00", "Review", "normal"), ("21:00", "22:00", "Personal time", "low"),
    ("22:00", "23:00", "Bed prep", "low"), ("23:00", "24:00", "Sleep", "low"),
]

BACKLOG_TITLES = [
    "Complete project report", "Fix login bug", "Update documentation",
    "Refactor API endpoint", "Write unit tests", "Review PR #42",
    "Deploy to staging", "Security audit", "Client presentation prep",
    "Database backup", "Update dependencies", "Performance tuning",
]

PRIORITY_DIST = {"urgent": 0.05, "high": 0.25, "normal": 0.50, "low": 0.20}
TYPE_DIST = {"scheduled": 0.70, "flexible": 0.30}
BACKLOG_PER_DAY = 8
PREPLAN_FRAC = 0.50

OUTPUT_DIR = BACKEND_ROOT / "models" / "retrained"


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def seed_data(db: Session, *, seed: int = 42) -> str:
    """Seed in-memory DB with routine + backlog tasks. Returns user_id."""
    r = _rng(seed)

    uid = new_id()
    db.add(User(id=uid, email=USER_EMAIL, password_hash="retrain",
                name="Retrain User", timezone=USER_TZ, role="user"))
    db.add(UserSchedulePreference(id=new_id(), user_id=uid,
        work_start_time="09:00", work_end_time="17:00",
        lunch_start_time="12:00", lunch_end_time="13:00",
        day_offs=["Saturday", "Sunday"], focus_hours=[]))
    db.flush()

    plan_dates: list[date] = []
    d = START_DATE
    while d <= END_DATE:
        plan_dates.append(d)
        d += timedelta(days=1)

    plan_ids: dict[date, str] = {}
    preplanned: list[tuple[str, date]] = []

    # --- PASS 1: Plans + routine tasks ---
    for plan_day in plan_dates:
        plan_str = plan_day.isoformat()
        tomorrow = plan_day + timedelta(days=1)
        ts = datetime(plan_day.year, plan_day.month, plan_day.day, 0, 0, 0, tzinfo=UTC)

        snap = ContextSnapshot(id=new_id(), user_id=uid, snapshot_type="retrain",
            context_payload={"plan_date": plan_str}, created_at=ts, updated_at=ts)
        plan = DailyPlan(id=new_id(), user_id=uid, plan_date=plan_str,
            status="confirmed", source="retrain", context_snapshot_id=snap.id,
            explanation=f"Plan for {plan_str}", created_at=ts, updated_at=ts)
        sched = Schedule(id=new_id(), user_id=uid, daily_plan_id=plan.id,
            schedule_date=plan_str, schedule_type="day", source="retrain",
            created_at=ts, updated_at=ts)
        db.add_all([snap, plan, sched])
        db.flush()  # plan + schedule now in DB
        plan_ids[plan_day] = plan.id

        # 24 routine tasks — batch flush for FK integrity
        routine_slots: list[tuple[str, str, str]] = []
        routine_tasks: list[Task] = []
        for start_clock, end_clock, label, priority in ROUTINE_SLOTS:
            tid = new_id()
            routine_slots.append((tid, start_clock, end_clock))
            routine_tasks.append(Task(id=tid, user_id=uid, daily_plan_id=plan.id,
                title=f"{plan_str} {start_clock} - {label}",
                description=f"Routine: {label}", estimated_duration=60,
                deadline=plan_str, task_type="scheduled", priority=priority,
                status="planned", tags=["routine"], completed_at=None,
                created_at=ts, updated_at=ts))
        db.add_all(routine_tasks)
        db.flush()

        # Lookup mapping for task titles
        task_by_id = {t.id: t for t in routine_tasks}
        routine_items = [
            ScheduleItem(id=new_id(), schedule_id=sched.id, task_id=tid,
                start_time=f"{plan_str}T{sc}:00", end_time=f"{plan_str}T{ec}:00",
                label=task_by_id[tid].title, status="planned", source="retrain",
                created_at=ts, updated_at=ts)
            for tid, sc, ec in routine_slots
        ]
        db.add_all(routine_items)
        db.flush()

        # 1 backlog task pre-planned for TOMORROW
        if tomorrow <= END_DATE:
            tid = new_id()
            db.add(Task(id=tid, user_id=uid, daily_plan_id=None,
                title=str(r.choice(BACKLOG_TITLES)),
                description="Backlog task for tomorrow",
                estimated_duration=int(r.integers(15, 120)),
                deadline=None, task_type=random_task_type(r),
                priority=random_priority(r), status="todo",
                tags=[], completed_at=None, created_at=ts, updated_at=ts))
            db.flush()
            preplanned.append((tid, plan_day))

    # --- PASS 1b: Link pre-planned tasks to tomorrow's plan ---
    for tid, plan_day in preplanned:
        tomorrow = plan_day + timedelta(days=1)
        if tomorrow not in plan_ids:
            continue
        db.execute(text("UPDATE tasks SET daily_plan_id = :pid WHERE id = :tid"),
                   {"pid": plan_ids[tomorrow], "tid": tid})
    db.flush()

    # --- PASS 2: Backlog tasks (created days ago, some pre-planned for tomorrow) ---
    for plan_day in plan_dates:
        tomorrow = plan_day + timedelta(days=1)
        if tomorrow > END_DATE or tomorrow not in plan_ids:
            continue
        tomorrow_pid = plan_ids[tomorrow]

        for _ in range(BACKLOG_PER_DAY):
            tid = new_id()
            offset = int(r.integers(2, 8))
            cd = plan_day - timedelta(days=offset)
            if cd < START_DATE:
                cd = START_DATE
            cts = datetime(cd.year, cd.month, cd.day, 0, 0, 0, tzinfo=UTC)

            planned = r.random() < PREPLAN_FRAC
            db.add(Task(id=tid, user_id=uid,
                daily_plan_id=tomorrow_pid if planned else None,
                title=str(r.choice(BACKLOG_TITLES)),
                description=f"Backlog for {plan_day}",
                estimated_duration=int(r.integers(15, 120)),
                deadline=None, task_type=random_task_type(r),
                priority=random_priority(r),
                status="planned" if planned else "todo",
                tags=[], completed_at=None, created_at=cts, updated_at=cts))
    db.flush()

    # --- Activity events ---
    all_tids = [row[0] for row in db.execute(
        text("SELECT id FROM tasks WHERE user_id = :uid"), {"uid": uid}).fetchall()]
    for tid in all_tids:
        if r.random() < 0.10:
            ed = START_DATE + timedelta(days=int(r.integers(2, (END_DATE - START_DATE).days - 2)))
            db.add(ActivityEvent(id=new_id(), user_id=uid, event_type="task_completed",
                entity_type="task", entity_id=tid, source="manual", payload={},
                occurred_at=datetime(ed.year, ed.month, ed.day, 10, 0, 0, tzinfo=UTC)))
    db.commit()

    total = db.execute(text("SELECT COUNT(*) FROM tasks WHERE user_id = :uid"), {"uid": uid}).scalar()
    plans = db.execute(text("SELECT COUNT(*) FROM daily_plans WHERE user_id = :uid"), {"uid": uid}).scalar()
    labeled = db.execute(text("SELECT COUNT(*) FROM tasks t WHERE t.user_id = :uid AND t.daily_plan_id IS NOT NULL"), {"uid": uid}).scalar()

    print(f"  User:        {uid[:8]}...")
    print(f"  Plans:       {plans}")
    print(f"  Tasks:       {total}")
    print(f"  With plan:   {labeled}")
    return uid


def random_priority(r: np.random.Generator) -> str:
    return str(r.choice(list(PRIORITY_DIST.keys()), p=list(PRIORITY_DIST.values())))


def random_task_type(r: np.random.Generator) -> str:
    return str(r.choice(list(TYPE_DIST.keys()), p=list(TYPE_DIST.values())))


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Retrain ML model with rich synthetic data")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-snapshots", type=int, default=15)
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    print("=" * 70)
    print("  RETRAIN ML MODEL")
    print("=" * 70)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        t0 = time.time()

        print(f"\n[1/4] Seeding data (seed={args.seed})...")
        uid = seed_data(db, seed=args.seed)
        print(f"  Time:        {time.time() - t0:.2f}s")

        print(f"\n[2/4] Building dataset ({SNAPSHOT_START} to {SNAPSHOT_END})...")
        t1 = time.time()
        df = build_dataset(db, SNAPSHOT_START, SNAPSHOT_END, user_id=uid, min_history_days=0)
        dt = time.time() - t1

        if df.empty:
            print("  ERROR: Empty dataset")
            return 1

        pos = int(df["label"].sum())
        neg = len(df) - pos
        print(f"  Rows:        {len(df)}")
        print(f"  Pos/Neg:     {pos}/{neg} ({pos/len(df)*100:.2f}% positive)")
        print(f"  Time:        {dt:.2f}s")

        print(f"\n[3/4] Training model...")
        t2 = time.time()
        metrics = train_pipeline(df, output_dir=str(output_dir), train_snapshots=args.train_snapshots)
        tt = time.time() - t2

        total_t = time.time() - t0
        mt = metrics.get("model_type", "?")
        f1 = metrics.get("f1", "?")
        auc = metrics.get("roc_auc", "?")
        print(f"\n  {'='*50}")
        print(f"  MODEL: {mt}    F1: {f1}    AUROC: {auc}")
        print(f"  Total time:  {total_t:.2f}s")
        print(f"  Saved:       {output_dir}/")

        summary = {"rows": len(df), "pos": pos, "neg": neg, "seed": args.seed,
                   "model": mt, "f1": f1, "auc": auc, "time_s": round(total_t, 2)}
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "retrain_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
