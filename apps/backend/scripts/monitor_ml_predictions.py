"""
Phase 6: ML Prediction Monitoring Script
=========================================

Reports on ML prediction quality, outcome reconciliation, and drift signals
by querying ``ml_prediction_logs`` and ``activity_events``.

Usage:
    python scripts/monitor_ml_predictions.py           # SQLite (in-memory + seed)
    python scripts/monitor_ml_predictions.py --db postgresql://...  # real DB

Output:
    - Total predictions logged
    - Score distribution by confidence band
    - Outcome breakdown (completed / skipped / deferred / pending)
    - Mean score trend (last 7 days vs all-time)
    - Model version summary
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure backend root is on sys.path
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import create_engine, text as sqltext
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings

SEP = "=" * 60


def _build_engine(db_url: str | None = None):
    """Create an engine — SQLite in-memory with seed data, or real DB from URL."""
    if db_url:
        return create_engine(db_url)

    # In-memory SQLite with fake seed data
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

    # Seed minimal data for demonstration
    user_id = "demo-user-0001"
    db.add(User(id=user_id, email="demo@example.com", name="Demo User", password_hash="x"))
    task_ids = []
    for i in range(5):
        tid = f"demo-task-{i:04d}"
        db.add(Task(id=tid, user_id=user_id, title=f"Demo Task {i}", task_type="scheduled"))
        task_ids.append(tid)
    plan_id = "demo-plan-0001"
    db.add(DailyPlan(id=plan_id, user_id=user_id, plan_date=(datetime.now(UTC).date() + timedelta(days=1)).isoformat(), status="draft", source="ml_boosted"))
    db.flush()

    # Seed ML predictions with varied scores
    now = datetime.now(UTC)
    predictions = [
        MLPredictionLog(user_id=user_id, plan_id=plan_id, task_id=tid,
                        prediction_score=score, confidence_band=band,
                        model_version="2026-07-27T12:50:47Z", model_type="LogisticRegression",
                        outcome=outcome,
                        outcome_updated_at=now - timedelta(hours=h) if outcome else None,
                        created_at=now - timedelta(hours=3),
                        updated_at=now - timedelta(hours=3))
        for tid, score, band, outcome, h in [
            ("demo-task-0000", 0.92, "high", "completed", 6),
            ("demo-task-0001", 0.78, "high", "completed", 12),
            ("demo-task-0002", 0.55, "medium", "deferred", 18),
            ("demo-task-0003", 0.30, "low", "pending", 0),
            ("demo-task-0004", 0.88, "high", "pending", 0),
        ]
    ]
    db.add_all(predictions)
    db.commit()
    db.close()
    return engine


def _fmt(val: object) -> str:
    """Format a value for display, handling None."""
    if val is None:
        return "—"
    return str(val)


def report(db: Session) -> int:
    """Run monitoring queries and print a summary report."""
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    # --- Totals ---
    total = db.execute(sqltext("SELECT COUNT(*) FROM ml_prediction_logs")).scalar() or 0
    recent = db.execute(
        sqltext("SELECT COUNT(*) FROM ml_prediction_logs WHERE created_at >= :since"),
        {"since": seven_days_ago},
    ).scalar() or 0

    print(SEP)
    print("  ML PREDICTION MONITORING REPORT")
    print(SEP)
    print(f"  Generated:     {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Total logs:    {total}")
    print(f"  Last 7 days:   {recent}")
    print()

    if total == 0:
        print("  No ML predictions logged yet.")
        return 0

    # --- Score distribution ---
    print("  -- Confidence Band Distribution --")
    bands = db.execute(
        sqltext("""
            SELECT confidence_band, COUNT(*) as cnt,
                   ROUND(AVG(prediction_score), 4) as avg_score
            FROM ml_prediction_logs
            GROUP BY confidence_band
            ORDER BY MIN(prediction_score) DESC
        """)
    ).fetchall()
    for band, cnt, avg in bands:
        pct = cnt / total * 100
        print(f"    {band:>8s}: {cnt:>5d} ({pct:>5.1f}%)  avg={avg}")
    print()

    # --- Outcome breakdown ---
    print("  -- Outcome Breakdown --")
    outcomes = db.execute(
        sqltext("""
            SELECT outcome, COUNT(*) as cnt
            FROM ml_prediction_logs
            GROUP BY outcome
            ORDER BY cnt DESC
        """)
    ).fetchall()
    for outcome, cnt in outcomes:
        pct = cnt / total * 100
        label = outcome if outcome else "unset"
        print(f"    {label:>12s}: {cnt:>5d} ({pct:>5.1f}%)")
    print()

    # --- High-confidence completion rate ---
    high_total = db.execute(
        sqltext("SELECT COUNT(*) FROM ml_prediction_logs WHERE confidence_band = 'high'")
    ).scalar() or 0
    high_completed = db.execute(
        sqltext("""
            SELECT COUNT(*) FROM ml_prediction_logs
            WHERE confidence_band = 'high' AND outcome = 'completed'
        """)
    ).scalar() or 0
    if high_total > 0:
        completion_rate = high_completed / high_total * 100
        print(f"  High-confidence completion rate: {high_completed}/{high_total} ({completion_rate:.1f}%)")
    print()

    # --- Mean score trend ---
    print("  -- Score Trend --")
    # Recent (last 7 days)
    recent_avg = db.execute(
        sqltext("""
            SELECT ROUND(AVG(prediction_score), 4), ROUND(MIN(prediction_score), 4),
                   ROUND(MAX(prediction_score), 4), COUNT(*)
            FROM ml_prediction_logs
            WHERE created_at >= :since
        """),
        {"since": seven_days_ago},
    ).fetchone()
    if recent_avg and recent_avg[3] and recent_avg[3] > 0:
        print(f"  Last 7 days:  avg={recent_avg[0]}  min={recent_avg[1]}  max={recent_avg[2]}  n={recent_avg[3]}")

    # All-time
    all_avg = db.execute(
        sqltext("""
            SELECT ROUND(AVG(prediction_score), 4), ROUND(MIN(prediction_score), 4),
                   ROUND(MAX(prediction_score), 4), COUNT(*)
            FROM ml_prediction_logs
        """)
    ).fetchone()
    if all_avg:
        print(f"  All time:     avg={all_avg[0]}  min={all_avg[1]}  max={all_avg[2]}  n={all_avg[3]}")
    print()

    # --- Model versions ---
    print("  -- Model Versions --")
    versions = db.execute(
        sqltext("""
            SELECT model_version, model_type, COUNT(*) as cnt
            FROM ml_prediction_logs
            GROUP BY model_version, model_type
            ORDER BY cnt DESC
        """)
    ).fetchall()
    for ver, mtype, cnt in versions:
        pct = cnt / total * 100
        print(f"    {_fmt(ver)[:30]:>30s}  {_fmt(mtype):>20s}  {cnt:>5d} ({pct:>5.1f}%)")
    print()

    # --- Drift signal: mean score shift ---
    if recent_avg and all_avg and all_avg[3] and all_avg[3] > 0 and recent_avg[3] and recent_avg[3] > 0:
        drift = recent_avg[0] - all_avg[0]
        drift_pct = drift / all_avg[0] * 100 if all_avg[0] else 0
        print(f"  Drift: recent mean vs all-time mean = {drift:+.4f} ({drift_pct:+.2f}%)")
        if abs(drift_pct) > 10:
            print("  [!] Mean score has shifted >10% — consider retraining or investigating.")
        else:
            print("  [OK] Mean score within expected range.")
    print(SEP)

    # Return 1 if drift exceeds threshold (for CI/alerting)
    if abs(drift_pct) > 10:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ML Prediction Monitoring Report")
    parser.add_argument("--db", type=str, default=None, help="Database URL (default: SQLite in-memory with seed)")
    parser.add_argument("--settings", action="store_true", help="Load DATABASE_URL from app settings")
    args = parser.parse_args()

    db_url = args.db
    if args.settings:
        settings = get_settings()
        db_url = settings.direct_url or settings.database_url

    engine = _build_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        return report(db)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
