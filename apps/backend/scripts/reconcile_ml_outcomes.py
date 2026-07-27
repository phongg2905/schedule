"""
Phase 6: ML Outcome Reconciliation Script
==========================================

Reconciles ``MLPredictionLog.outcome`` against ``ActivityEvent`` records
so that monitoring reports have accurate completion/skip/deferral rates.

Logic:
  1. Fetch all prediction logs where outcome is NULL or 'pending'.
  2. Batch-query ``activity_events`` for task events (task_completed,
     task_skipped, task_delayed) that occurred after the prediction was logged.
  3. For each prediction, pick the *preferred* outcome among matching events.
  4. Batch-update the outcome + outcome_updated_at fields.

Usage:
    python scripts/reconcile_ml_outcomes.py           # SQLite in-memory (demo)
    python scripts/reconcile_ml_outcomes.py --db postgresql://...  # real DB
    python scripts/reconcile_ml_outcomes.py --settings  # load from app config
    python scripts/reconcile_ml_outcomes.py --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import create_engine, text as sqltext
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings

SEP = "=" * 60

# Map ActivityEvent event_type -> MLPredictionLog outcome value
_EVENT_TO_OUTCOME: dict[str, str] = {
    "task_completed": "completed",
    "task_skipped": "skipped",
    "task_delayed": "deferred",
    "task_deferred": "deferred",
}

# Outcome precedence: when multiple events exist, pick the most informative
_OUTCOME_PRECEDENCE = ["completed", "deferred", "skipped"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_utc_dt(val: Any) -> datetime | None:
    """Normalize a datetime-or-string to a tz-aware UTC datetime, or None."""
    if isinstance(val, datetime):
        return val.replace(tzinfo=UTC) if val.tzinfo is None else val
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
        except (ValueError, TypeError):
            pass
    return None


# ---------------------------------------------------------------------------
# DB engine builder
# ---------------------------------------------------------------------------


def _build_engine(db_url: str | None = None):
    """Create an engine — SQLite in-memory with seed data, or real DB from URL."""
    if db_url:
        return create_engine(db_url)

    # In-memory SQLite with demo seed data
    from src.db.base import Base
    from src.db.models import DailyPlan, MLPredictionLog, Task, User  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Seed demo data using ORM (handles defaults automatically)
    from src.db.models import ActivityEvent, User  # noqa: F811

    now = datetime.now(UTC)
    uid = "demo-reconcile-user"
    plan_id = "demo-reconcile-plan"

    db.add(User(id=uid, email="reconcile@demo.dev", password_hash="x",
               name="Reconcile Demo", timezone="Asia/Saigon", role="user"))
    db.add(DailyPlan(id=plan_id, user_id=uid,
                     plan_date=(now.date() + timedelta(days=1)).isoformat(),
                     status="draft", source="ml_boosted"))

    task_ids = []
    for i in range(5):
        tid = f"demo-rtask-{i:04d}"
        db.add(Task(id=tid, user_id=uid, title=f"Task {i}", task_type="scheduled"))
        task_ids.append(tid)
    db.flush()

    # Seed predictions with different outcomes
    predictions = [
        # tid,                    score, band,      activity_event_type, hrs_after_pred
        (task_ids[0], 0.92, "high", "task_completed", 2),
        (task_ids[1], 0.78, "high", "task_completed", 5),
        (task_ids[2], 0.55, "medium", "task_delayed", 3),
        (task_ids[3], 0.30, "low", "task_skipped", 1),
        (task_ids[4], 0.88, "high", None, None),  # no event -> stays pending
    ]

    for tid, score, band, event_type, hrs_delay in predictions:
        pred_time = now - timedelta(hours=24)
        db.add(MLPredictionLog(
            id=f"pred-{tid}", user_id=uid, plan_id=plan_id, task_id=tid,
            prediction_score=score, confidence_band=band,
            model_version="2026-07-27T12:50:47Z", model_type="LogisticRegression",
            outcome="pending",
            created_at=pred_time, updated_at=pred_time,
        ))

        if event_type and hrs_delay is not None:
            event_time = pred_time + timedelta(hours=hrs_delay)
            db.add(ActivityEvent(
                id=f"evt-{tid}", user_id=uid, event_type=event_type,
                entity_type="task", entity_id=tid, source="manual",
                payload={}, occurred_at=event_time,
            ))

    db.commit()
    db.close()
    return engine


# ---------------------------------------------------------------------------
# Core reconciliation logic
# ---------------------------------------------------------------------------


def reconcile(db: Session, dry_run: bool = False) -> int:
    """Reconcile pending ML predictions against activity events.

    Returns the number of rows eligible for update.
    """
    now = _ensure_utc_dt(datetime.now(UTC))

    # --- 1. Find all pending predictions ---
    pending = db.execute(sqltext(
        "SELECT id, task_id, created_at "
        "FROM ml_prediction_logs "
        "WHERE outcome IS NULL OR outcome = 'pending' "
        "ORDER BY created_at ASC"
    )).fetchall()

    if not pending:
        print("  No pending predictions found -- nothing to reconcile.")
        return 0

    print(f"  Found {len(pending)} prediction(s) pending reconciliation.")
    print()

    # --- 2. Collect unique task IDs ---
    task_ids = list({row[1] for row in pending})

    # --- 3. Batch-query activity events for these tasks ---
    if not task_ids:
        return 0

    quoted = [f"'{tid}'" for tid in task_ids]
    in_clause = ", ".join(quoted)

    events = db.execute(sqltext(
        f"SELECT entity_id, event_type, occurred_at "
        f"FROM activity_events "
        f"WHERE entity_type = 'task' "
        f"  AND entity_id IN ({in_clause}) "
        f"  AND event_type IN ('task_completed', 'task_skipped', 'task_delayed', 'task_deferred') "
        f"ORDER BY entity_id, occurred_at DESC"
    )).fetchall()

    # --- 4. Build {task_id: [(event_type, occurred_at), ...]} lookup ---
    task_events: dict[str, list[tuple[str, datetime]]] = {}
    for entity_id, event_type, occurred_at in events:
        evt_time = _ensure_utc_dt(occurred_at)
        if evt_time is not None:
            task_events.setdefault(entity_id, []).append((event_type, evt_time))

    # --- 5. For each prediction, find the best matching outcome ---
    updates: list[dict[str, Any]] = []  # params list for batch executemany
    for pred_id, task_id, created_at in pending:
        pred_time = _ensure_utc_dt(created_at)
        if pred_time is None:
            continue

        events_for_task = task_events.get(task_id, [])

        # Filter events that happened AFTER the prediction
        future_events = [
            (evt_type, evt_time)
            for evt_type, evt_time in events_for_task
            if evt_time > pred_time
        ]

        if not future_events:
            continue

        # Pick the highest-precedence outcome among future events
        matched_outcome = "pending"
        outcome_time: datetime | None = None
        for evt_type, evt_time in future_events:
            outcome = _EVENT_TO_OUTCOME.get(evt_type, "pending")
            if outcome == "pending":
                continue
            # First match wins (highest precedence since events are ordered by occurred_at DESC)
            if matched_outcome == "pending":
                matched_outcome = outcome
                outcome_time = evt_time
            else:
                current_rank = _OUTCOME_PRECEDENCE.index(matched_outcome)
                candidate_rank = _OUTCOME_PRECEDENCE.index(outcome)
                if candidate_rank < current_rank:
                    matched_outcome = outcome
                    outcome_time = evt_time

        if matched_outcome != "pending" and outcome_time:
            updates.append({
                "id": pred_id,
                "outcome": matched_outcome,
                "outcome_at": outcome_time,
                "now": now,
            })

    # --- 6. Report ---
    n_updated = len(updates)
    if n_updated == 0:
        print("  No matching events found -- all predictions remain pending.")
        return 0

    print(f"  Reconciled outcomes for {n_updated} prediction(s):")
    for u in updates:
        short_id = u["id"][-12:] if len(u["id"]) > 12 else u["id"]
        outcome = u["outcome"]
        ts = u["outcome_at"].strftime("%Y-%m-%d %H:%M") if isinstance(u["outcome_at"], datetime) else str(u["outcome_at"])[:16]
        print(f"    [{outcome:>10s}] {short_id} @ {ts}")

    if dry_run:
        print(f"\n  [DRY RUN] Would update {n_updated} row(s). No changes written.")
        return n_updated

    # --- 7. Batch UPDATE (executemany for efficiency) ---
    db.execute(
        sqltext(
            "UPDATE ml_prediction_logs "
            "SET outcome = :outcome, "
            "    outcome_updated_at = :outcome_at, "
            "    updated_at = :now "
            "WHERE id = :id"
        ),
        updates,
    )
    db.commit()
    print(f"\n  [OK] Updated {n_updated} row(s).")
    return n_updated


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile ML prediction outcomes against activity events"
    )
    parser.add_argument("--db", type=str, default=None,
                        help="Database URL (default: SQLite in-memory with demo)")
    parser.add_argument("--settings", action="store_true",
                        help="Load DATABASE_URL from app settings")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    args = parser.parse_args()

    db_url = args.db
    if args.settings:
        settings = get_settings()
        db_url = settings.direct_url or settings.database_url

    print(SEP)
    print("  ML OUTCOME RECONCILIATION")
    if args.dry_run:
        print("  [DRY RUN -- no changes will be written]")
    print(SEP)

    engine = _build_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        n = reconcile(db, dry_run=args.dry_run)
        print(SEP)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
