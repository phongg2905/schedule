"""
Phase 2: Dataset Build — Snapshot Extraction Job
===================================================

Generates a reproducible training dataset for next-day task prediction.

For each (user, snapshot_date=D), extracts:
  - All candidate tasks that existed at end of D
  - Features computed from data available at or before end of D
  - Label = 1 if task was included in D+1's daily plan, else 0

Usage:
    python scripts/build_ml_dataset.py \\
        --from-date 2026-07-07 \\
        --to-date 2026-08-02 \\
        --output data/training_dataset.parquet \\
        [--user-id <uuid>]              # optional: restrict to one user
        [--min-history-days 2]          # min days of user history to include
        [--batch-size 50000]            # rows per batch (memory management)

Guarantees:
    - No data leakage: features only use data <= end of snapshot day D.
    - Labels come from D+1 daily plan only.
    - Output is deterministic (same DB → same dataset).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Path setup — allow running as `python scripts/...` from the backend directory
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.config import get_settings
from src.db.session import get_session_factory

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LOOKBACK_DAYS = 7  # how many days of history to look back for features
MAX_SAFE_INT = 9999  # sentinel for null/missing numeric values
DEFAULT_ESTIMATED_DURATION = 30  # fallback for missing duration
WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]
OUTPUT_DIR = BACKEND_ROOT / "data"

# ---------------------------------------------------------------------------
# Timezone helpers (stdlib zoneinfo — no extra deps)
# ---------------------------------------------------------------------------

_TIMEZONE_CACHE: dict[str, ZoneInfo] = {}


def _get_tz(tz_name: str) -> ZoneInfo:
    """Get ZoneInfo object (cached)."""
    if tz_name not in _TIMEZONE_CACHE:
        _TIMEZONE_CACHE[tz_name] = ZoneInfo(tz_name)
    return _TIMEZONE_CACHE[tz_name]


def compute_end_of_day(d: date, timezone_str: str) -> datetime:
    """Return the end of calendar day D in the user's timezone, as UTC datetime.

    Returns a timezone-aware datetime (UTC) to match DB DateTime(timezone=True).

    Example: D=2026-07-26, tz=Asia/Saigon (UTC+7)
             -> 2026-07-26T23:59:59+07:00 -> 2026-07-26T16:59:59+00:00
    """
    tz = _get_tz(timezone_str)
    end_local = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=tz)
    return end_local.astimezone(UTC)


def date_from_iso(s: str | None) -> date | None:
    """Safely parse YYYY-MM-DD string to date (stdlib)."""
    if s is None:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# DB query helpers
# ---------------------------------------------------------------------------

_BATCH_SIZE = 10000  # rows per fetch chunk for large queries


def _get_user_timezones(db: Session) -> dict[str, str]:
    """Return {user_id: timezone} for all active users."""
    rows = db.execute(
        text("SELECT id, timezone FROM users WHERE deleted_at IS NULL")
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _get_user_ids(db: Session, restrict_to: str | None = None) -> list[str]:
    """Return list of user IDs, optionally restricted."""
    if restrict_to:
        return [restrict_to]
    rows = db.execute(
        text("SELECT id FROM users WHERE deleted_at IS NULL")
    ).fetchall()
    return [row[0] for row in rows]


def _user_has_enough_history(
    db: Session, user_id: str, min_days: int, snapshot_date: date
) -> bool:
    """Check if user has at least min_days of data before snapshot_date."""
    first_event = db.execute(
        text(
            """
            SELECT MIN(occurred_at) FROM activity_events
            WHERE user_id = :uid AND occurred_at <= :end_of_day
            """
        ),
        {
            "uid": user_id,
            "end_of_day": compute_end_of_day(snapshot_date, "UTC").isoformat(),
        },
    ).scalar()
    if first_event is None:
        # Check if user has any tasks created before snapshot
        first_task = db.execute(
            text(
                """
                SELECT MIN(created_at) FROM tasks
                WHERE user_id = :uid AND created_at <= :end_of_day
                """
            ),
            {
                "uid": user_id,
                "end_of_day": compute_end_of_day(snapshot_date, "UTC").isoformat(),
            },
        ).scalar()
        first_event = first_task
    if first_event is None:
        return False
    # SQLite returns datetime as string from raw scalar queries; normalize
    days = (snapshot_date - _ensure_dt(first_event).date()).days
    return days >= min_days


# ---------------------------------------------------------------------------
# SQLite safety: raw text() queries return datetime columns as strings on SQLite
# ---------------------------------------------------------------------------


def _ensure_dt(val: Any) -> datetime | Any:
    """Convert string datetime from SQLite to proper datetime object.

    PostgreSQL returns datetime objects from raw text() queries, but SQLite
    returns strings. This helper normalizes both cases.
    """
    if isinstance(val, str):
        try:
            # Try ISO format: 2026-07-10T00:00:00 or 2026-07-10 00:00:00
            val = val.replace("T", " ")[:26]
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=UTC)
        except (ValueError, TypeError):
            try:
                return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            except (ValueError, TypeError):
                pass
    return val


def _parse_json_list(val: Any) -> list[str]:
    """Parse a JSON column value, handling both parsed lists and raw strings.

    PostgreSQL returns JSON columns as Python lists from raw text() queries;
    SQLite returns them as JSON-encoded strings. This normalizes both.
    """
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return []


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def _get_candidate_tasks(
    db: Session, user_id: str, end_of_d: datetime
) -> list[dict]:
    """Return candidate tasks that existed at end of day D.

    A task is a candidate if:
      - It was created on or before end_of_D
      - It was NOT soft-deleted before end_of_D
      - It was NOT completed before end_of_D  (completed_at > end_of_D means still open)
    """
    rows = db.execute(
        text(
            """
            SELECT
                t.id,
                t.title,
                t.description,
                t.estimated_duration,
                t.deadline,
                t.start_time,
                t.task_type,
                t.priority,
                t.status,
                t.tags,
                t.completed_at,
                t.created_at,
                t.updated_at,
                t.daily_plan_id,
                dp.plan_date AS assigned_plan_date
            FROM tasks t
            LEFT JOIN daily_plans dp ON dp.id = t.daily_plan_id
            WHERE t.user_id = :uid
              AND (t.deleted_at IS NULL OR t.deleted_at > :end_of_d)
              AND (t.completed_at IS NULL OR t.completed_at > :end_of_d)
              AND t.created_at <= :end_of_d
            ORDER BY t.created_at
            """
        ),
        {"uid": user_id, "end_of_d": end_of_d},
    ).fetchall()

    return [
        {
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "estimated_duration": r[3],
            "deadline": r[4],
            "start_time": r[5],
            "task_type": r[6],
            "priority": r[7] or "normal",
            "status": r[8],
            "tags": r[9] if isinstance(r[9], list) else [],
            "completed_at": _ensure_dt(r[10]),
            "created_at": _ensure_dt(r[11]),
            "updated_at": _ensure_dt(r[12]),
            "daily_plan_id": r[13],
            "assigned_plan_date": r[14],
        }
        for r in rows
    ]


def _compute_task_features(
    task: dict, snapshot_date: date, end_of_d: datetime
) -> dict[str, Any]:
    """Compute feature vector for a single task at snapshot date D."""
    features: dict[str, Any] = {}

    created_at: datetime = task["created_at"]
    # Need to handle created_at being timezone-aware or naive
    if created_at.tzinfo is not None:
        created_at_utc = created_at.astimezone(UTC).replace(tzinfo=None)
    else:
        created_at_utc = created_at

    # Task age at snapshot
    features["task_age_days"] = max(0, (snapshot_date - created_at_utc.date()).days)

    # Deadline features
    deadline = date_from_iso(task["deadline"])
    features["has_deadline"] = deadline is not None
    features["is_overdue"] = bool(deadline and deadline < snapshot_date)
    if deadline:
        features["deadline_relative_days"] = (deadline - snapshot_date).days
    else:
        features["deadline_relative_days"] = MAX_SAFE_INT

    # Estimated duration
    dur = task["estimated_duration"]
    features["estimated_duration"] = dur if dur is not None else DEFAULT_ESTIMATED_DURATION
    features["has_estimated_duration"] = dur is not None

    # Priority (one-hot)
    pri = (task["priority"] or "normal").lower()
    features["priority_urgent"] = pri == "urgent"
    features["priority_high"] = pri == "high"
    features["priority_normal"] = pri == "normal"
    features["priority_low"] = pri == "low"

    # Task type
    ttype = task["task_type"] or "scheduled"
    features["task_type_scheduled"] = ttype == "scheduled"
    features["task_type_flexible"] = ttype == "flexible"

    # Tags
    tags = task["tags"] or []
    features["num_tags"] = len(tags)

    # Description
    has_desc = bool(task["description"])
    features["has_description"] = has_desc
    features["description_length"] = len(task["description"]) if has_desc else 0

    return features


# Event type → status mapping for reconstruction
_STATUS_EVENT_MAP = {
    "task_completed": "completed",
    "task_skipped": "skipped",
    "task_delayed": "deferred",
    "task_moved": "todo",
    "task_created": "todo",
}


def _batch_reconstruct_statuses(
    db: Session,
    user_id: str,
    task_ids: list[str],
    end_of_d: datetime,
) -> dict[str, str]:
    """Reconstruct task statuses at end_of_d for ALL tasks (single query).

    Portable across PostgreSQL and SQLite.
    Returns: {task_id: status_string}
    """
    if not task_ids:
        return {}

    # Build a safe IN clause (task IDs are UUIDs, so this is injection-safe)
    quoted = [f"'{tid}'" for tid in task_ids]
    in_clause = ", ".join(quoted)

    sql = text(
        f"""
        SELECT entity_id, event_type, occurred_at
        FROM activity_events
        WHERE user_id = :uid
          AND entity_type = 'task'
          AND entity_id IN ({in_clause})
          AND occurred_at <= :end_of_d
          AND event_type IN ('task_completed', 'task_skipped', 'task_delayed', 'task_moved', 'task_created')
        ORDER BY entity_id, occurred_at DESC
        """
    )
    rows = db.execute(sql, {"uid": user_id, "end_of_d": end_of_d}).fetchall()

    # Take the first (latest) event per task_id from the sorted results
    result: dict[str, str] = {tid: "todo" for tid in task_ids}
    seen: set[str] = set()
    for entity_id, event_type, _occurred_at in rows:
        if entity_id not in seen:
            result[entity_id] = _STATUS_EVENT_MAP.get(event_type, "todo")
            seen.add(entity_id)
    return result


def _batch_get_event_counts(
    db: Session,
    user_id: str,
    task_ids: list[str],
    end_of_d: datetime,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, dict[str, int]]:
    """Get event counts for ALL tasks in one query.

    Portable across PostgreSQL and SQLite.
    Returns: {task_id: {completion_count_7d, deferral_count_7d, ...}}
    """
    if not task_ids:
        return {}

    lookback_start = end_of_d - timedelta(days=lookback_days)

    # Build a safe IN clause (task IDs are UUIDs, so this is injection-safe)
    quoted = [f"'{tid}'" for tid in task_ids]
    in_clause = ", ".join(quoted)

    sql = text(
        f"""
        SELECT entity_id, event_type, occurred_at
        FROM activity_events
        WHERE user_id = :uid
          AND entity_type = 'task'
          AND entity_id IN ({in_clause})
          AND occurred_at > :lookback_start
          AND occurred_at <= :end_of_d
        ORDER BY entity_id, occurred_at DESC
        """
    )
    rows = db.execute(
        sql,
        {
            "uid": user_id,
            "lookback_start": lookback_start,
            "end_of_d": end_of_d,
        },
    ).fetchall()

    # Initialize defaults
    result: dict[str, dict[str, int]] = {
        tid: {
            "completion_count_7d": 0,
            "deferral_count_7d": 0,
            "move_count_7d": 0,
            "skip_count_7d": 0,
            "update_count_7d": 0,
            "days_since_last_completion": MAX_SAFE_INT,
        }
        for tid in task_ids
    }

    for entity_id, event_type, occurred_at in rows:
        # SQLite returns datetime as string from raw queries; normalize
        occurred_at = _ensure_dt(occurred_at)
        feats = result[entity_id]
        if event_type == "task_completed":
            feats["completion_count_7d"] += 1
            days_since = max(0, (end_of_d - occurred_at).days)
            if days_since < feats["days_since_last_completion"]:
                feats["days_since_last_completion"] = days_since
        elif event_type in ("task_delayed", "task_deferred"):
            feats["deferral_count_7d"] += 1
        elif event_type == "task_moved":
            feats["move_count_7d"] += 1
        elif event_type == "task_skipped":
            feats["skip_count_7d"] += 1
        elif event_type == "task_updated":
            feats["update_count_7d"] += 1

    return result


def _get_user_context_features(
    db: Session,
    user_id: str,
    end_of_d: datetime,
    timezone_str: str,
    target_date: date,
    snapshot_date: date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, Any]:
    """Compute user-level context features (single aggregate query).

    Originally 6 separate queries; now 1 query with 6 subqueries + 1 query
    for activity_events (which has different filter conditions).
    """
    lookback_start = end_of_d - timedelta(days=lookback_days)
    lookback_date_str = (snapshot_date - timedelta(days=lookback_days)).isoformat()
    target_date_str = target_date.isoformat()

    # Single aggregate query: all user-level counts + last plan + event count
    row = db.execute(
        text(
            """
            SELECT
                -- total open tasks
                (SELECT COUNT(*) FROM tasks
                 WHERE user_id = :uid
                   AND (deleted_at IS NULL OR deleted_at > :end_of_d)
                   AND (completed_at IS NULL OR completed_at > :end_of_d)
                   AND created_at <= :end_of_d
                ) AS total_open,

                -- scheduled tasks count
                (SELECT COUNT(*) FROM tasks
                 WHERE user_id = :uid
                   AND task_type = 'scheduled'
                   AND (deleted_at IS NULL OR deleted_at > :end_of_d)
                   AND (completed_at IS NULL OR completed_at > :end_of_d)
                   AND created_at <= :end_of_d
                ) AS scheduled_count,

                -- flexible tasks count
                (SELECT COUNT(*) FROM tasks
                 WHERE user_id = :uid
                   AND task_type = 'flexible'
                   AND (deleted_at IS NULL OR deleted_at > :end_of_d)
                   AND (completed_at IS NULL OR completed_at > :end_of_d)
                   AND created_at <= :end_of_d
                ) AS flexible_count,

                -- tasks planned in lookback window
                (SELECT COUNT(DISTINCT t.id) FROM tasks t
                 JOIN daily_plans dp ON dp.id = t.daily_plan_id
                 WHERE t.user_id = :uid
                   AND (t.deleted_at IS NULL OR t.deleted_at > :end_of_d)
                   AND dp.plan_date >= :lookback_date_str
                   AND dp.plan_date < :target_date_str
                ) AS planned_in_window,

                -- tasks completed in lookback window
                (SELECT COUNT(DISTINCT entity_id) FROM activity_events
                 WHERE user_id = :uid
                   AND entity_type = 'task'
                   AND event_type = 'task_completed'
                   AND occurred_at > :lookback_start
                   AND occurred_at <= :end_of_d
                ) AS completed_in_window,

                -- last plan date before target
                (SELECT MAX(plan_date) FROM daily_plans
                 WHERE user_id = :uid
                   AND plan_date < :target_date_str
                ) AS last_plan_date
            """
        ),
        {
            "uid": user_id,
            "end_of_d": end_of_d,
            "lookback_start": lookback_start,
            "lookback_date_str": lookback_date_str,
            "target_date_str": target_date_str,
        },
    ).fetchone()

    total_open = row[0] or 0
    scheduled_count = row[1] or 0
    flexible_count = row[2] or 0
    planned_in_window = row[3] or 0
    completed_in_window = row[4] or 0
    last_plan_str = row[5]

    # Completion rate
    completion_rate = (
        completed_in_window / planned_in_window
        if planned_in_window > 0
        else 0.5
    )

    # Days since last plan
    days_since_last_plan = MAX_SAFE_INT
    if last_plan_str:
        last_plan_date = date_from_iso(str(last_plan_str))
        if last_plan_date:
            days_since_last_plan = (snapshot_date - last_plan_date).days
            if days_since_last_plan < 0:
                days_since_last_plan = 0

    return {
        "user_total_open_tasks": total_open,
        "user_scheduled_count": scheduled_count,
        "user_flexible_count": flexible_count,
        "user_completion_rate_7d": round(completion_rate, 4),
        "user_completed_count_7d": completed_in_window,
        "user_planned_count_7d": planned_in_window,
        "days_since_last_plan": days_since_last_plan,
    }


def _get_temporal_features(
    target_date: date, is_day_off: bool
) -> dict[str, Any]:
    """Compute temporal features for target date D+1."""
    # Day of week: Monday=0, Sunday=6
    dow = target_date.weekday()
    return {
        "target_day_of_week": dow,
        "target_is_monday": dow == 0,
        "target_is_friday": dow == 4,
        "target_is_weekend": dow >= 5,
        "target_weekday_name": WEEKDAY_NAMES[dow],
        "target_is_day_off": is_day_off,
    }


def _get_preferences(
    db: Session, user_id: str
) -> dict[str, Any]:
    """Get user schedule preferences (single query)."""
    row = db.execute(
        text(
            """
            SELECT
                u.timezone,
                usp.work_start_time,
                usp.work_end_time,
                usp.lunch_start_time,
                usp.lunch_end_time,
                usp.day_offs,
                usp.focus_hours
            FROM users u
            LEFT JOIN user_schedule_preferences usp ON usp.user_id = u.id
            WHERE u.id = :uid
            """
        ),
        {"uid": user_id},
    ).fetchone()

    if row is None:
        return {
            "timezone": "Asia/Saigon",
            "work_start": "09:00",
            "work_end": "17:00",
            "lunch_start": "12:00",
            "lunch_end": "13:00",
            "day_offs": [],
            "focus_hours": [],
        }

    day_offs = _parse_json_list(row[5])
    focus_hours = _parse_json_list(row[6])

    return {
        "timezone": row[0] or "Asia/Saigon",
        "work_start": row[1] or "09:00",
        "work_end": row[2] or "17:00",
        "lunch_start": row[3] or "12:00",
        "lunch_end": row[4] or "13:00",
        "day_offs": day_offs,
        "focus_hours": focus_hours,
    }


# ---------------------------------------------------------------------------
# Label assignment
# ---------------------------------------------------------------------------


def _get_plan_for_date(
    db: Session, user_id: str, target_date: date
) -> tuple[str, str] | None:
    """Fetch the (id, status) of a user's daily plan for a date.

    Returns None if no plan exists or plan is in draft status.
    Cached at snapshot level to avoid per-task queries.
    """
    target_str = target_date.isoformat()
    plan = db.execute(
        text(
            """
            SELECT id, status FROM daily_plans
            WHERE user_id = :uid AND plan_date = :target_date
            LIMIT 1
            """
        ),
        {"uid": user_id, "target_date": target_str},
    ).fetchone()

    if plan is None:
        return None

    plan_id, plan_status = plan
    if plan_status in ("draft",):
        return None  # Draft plans don't count

    return (plan_id, plan_status)


def _get_label(
    db: Session,
    task_id: str,
    plan_id: str,
    *,
    pre_fetched_task_plan_id: str | None = None,
) -> int:
    """Determine if a task was included in a given daily plan.

    Args:
        db: DB session
        task_id: Task to check
        plan_id: Daily plan ID (pre-fetched at snapshot level)
        pre_fetched_task_plan_id: Task's current daily_plan_id (cached)

    Returns 1 if the task was in the plan, 0 otherwise.
    """
    # Method 1: Check task.daily_plan_id (use cached value to avoid re-query)
    if pre_fetched_task_plan_id == plan_id:
        return 1

    # Method 2: Check if task appears in a ScheduleItem of this plan
    in_schedule = db.execute(
        text(
            """
            SELECT 1 FROM schedule_items si
            JOIN schedules s ON s.id = si.schedule_id
            JOIN daily_plans dp ON dp.id = s.daily_plan_id
            WHERE dp.id = :plan_id
              AND si.task_id = :task_id
            LIMIT 1
            """
        ),
        {"plan_id": plan_id, "task_id": task_id},
    ).scalar()

    return 1 if in_schedule else 0


# ---------------------------------------------------------------------------
# Main extraction loop
# ---------------------------------------------------------------------------


def _build_rows_for_snapshot(
    db: Session,
    user_id: str,
    snapshot_date: date,
    prefs: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build training rows for one (user, snapshot_date=D).

    This function processes ALL candidate tasks in batch queries to avoid
    the O(n) per-task query issue.
    """
    timezone_str = prefs["timezone"]
    day_offs = prefs["day_offs"] or []
    end_of_d = compute_end_of_day(snapshot_date, timezone_str)
    target_date = snapshot_date + timedelta(days=1)

    # --- Candidate tasks (single query with LEFT JOIN to check plan date) ---
    candidates = _get_candidate_tasks(db, user_id, end_of_d)
    if not candidates:
        return []

    task_ids = [t["id"] for t in candidates]

    # --- Batch: reconstruct statuses for ALL tasks (one query) ---
    status_map = _batch_reconstruct_statuses(db, user_id, task_ids, end_of_d)

    # --- Batch: event counts for ALL tasks (one query) ---
    event_counts = _batch_get_event_counts(db, user_id, task_ids, end_of_d)

    # --- Temporal features (same for all tasks in this snapshot) ---
    weekday_name = target_date.strftime("%A")
    is_day_off = weekday_name in day_offs
    temporal_feats = _get_temporal_features(target_date, is_day_off)
    temporal_feats["target_date"] = target_date.isoformat()
    temporal_feats["snapshot_date"] = snapshot_date.isoformat()

    # --- User context features (same for all tasks) ---
    user_feats = _get_user_context_features(
        db, user_id, end_of_d, timezone_str, target_date, snapshot_date
    )
    user_feats["user_timezone"] = timezone_str

    # --- Cache: fetch the target plan once (shared by all tasks) ---
    target_plan = _get_plan_for_date(db, user_id, target_date)

    # --- Build rows ---
    snapshot_str = snapshot_date.isoformat()
    rows: list[dict[str, Any]] = []

    for task in candidates:
        tid = task["id"]

        # Task features
        task_feats = _compute_task_features(task, snapshot_date, end_of_d)

        # Status at D (from batch)
        status_at_d = status_map.get(tid, "todo")
        task_feats["status_at_d"] = status_at_d
        task_feats["status_is_planned"] = status_at_d == "planned"
        task_feats["status_is_deferred"] = status_at_d == "deferred"
        task_feats["status_is_skipped"] = status_at_d == "skipped"

        # ⚠️ LEAKAGE PREVENTION: daily_plan_id field is LIVE and may already
        # point to D+1's plan if the user pre-generated it.
        # Use assigned_plan_date from the LEFT JOIN instead:
        # only count as "already planned" if plan_date <= snapshot_date
        assigned_date = task.get("assigned_plan_date")
        has_plan_for_past = bool(
            assigned_date and assigned_date <= snapshot_str
        )
        task_feats["has_plan_for_past_or_today"] = has_plan_for_past

        # History features (from batch)
        hist_feats = event_counts.get(tid, {
            "completion_count_7d": 0,
            "deferral_count_7d": 0,
            "move_count_7d": 0,
            "skip_count_7d": 0,
            "update_count_7d": 0,
            "days_since_last_completion": MAX_SAFE_INT,
        })

        # Label (plan already cached at snapshot level)
        if target_plan:
            plan_id, _plan_status = target_plan
            label = _get_label(
                db, tid, plan_id,
                pre_fetched_task_plan_id=task.get("daily_plan_id"),
            )
        else:
            label = 0

        # Assemble row
        row: dict[str, Any] = {
            "snapshot_date": snapshot_str,
            "target_date": target_date.isoformat(),
            "user_id": user_id,
            "task_id": tid,
            "task_title_hint": task["title"][:50],  # For debugging only; dropped before export
            **task_feats,
            **hist_feats,
            **user_feats,
            **temporal_feats,
            "label": label,
        }
        rows.append(row)

    return rows


def build_dataset(
    db: Session,
    from_date: date,
    to_date: date,
    *,
    user_id: str | None = None,
    min_history_days: int = 2,
    batch_size: int = 50000,
) -> pd.DataFrame:
    """Main entry point: build the full training dataset.

    Args:
        db: SQLAlchemy session
        from_date: First snapshot date (inclusive)
        to_date: Last snapshot date (inclusive). target_date = snapshot + 1
        user_id: Optional user ID to restrict to
        min_history_days: Minimum days of history a user needs before snapshot
        batch_size: Rows per batch for progress reporting

    Returns:
        DataFrame with training rows.
    """
    all_rows: list[pd.DataFrame] = []
    row_count = 0
    users_processed = 0

    user_ids = _get_user_ids(db, restrict_to=user_id)
    user_tz_map = _get_user_timezones(db)

    total_dates = (to_date - from_date).days + 1
    print(f"Date range: {from_date} to {to_date} ({total_dates} snapshot dates)")
    print(f"Users to process: {len(user_ids)}")

    for uid in user_ids:
        if not _user_has_enough_history(db, uid, min_history_days, from_date):
            continue

        # Pre-fetch user preferences once
        prefs = _get_preferences(db, uid)
        users_processed += 1
        user_rows = 0

        current_date = from_date
        while current_date <= to_date:
            target_date = current_date + timedelta(days=1)
            if target_date > date.today():
                break

            rows = _build_rows_for_snapshot(db, uid, current_date, prefs)
            if rows:
                df = pd.DataFrame(rows)
                all_rows.append(df)
                row_count += len(df)
                user_rows += len(df)

                if row_count % batch_size < len(rows):
                    print(
                        f"  [{row_count:>8} rows] "
                        f"user={uid[:8]}... "
                        f"D={current_date} "
                        f"target={target_date} "
                        f"candidates={len(rows)}"
                    )

            current_date += timedelta(days=1)

        print(
            f"User {uid[:8]}... done: {user_rows} rows "
            f"(tz={prefs['timezone']})"
        )

    if not all_rows:
        print("WARNING: No training rows generated! Check data availability.")
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    print(f"\nDataset complete: {len(result)} rows, {result['label'].sum()} positive labels")
    print(f"Label distribution:\n{result['label'].value_counts().to_string()}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ML training dataset for next-day task prediction"
    )
    parser.add_argument(
        "--from-date",
        required=True,
        type=str,
        help="First snapshot date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        required=True,
        type=str,
        help="Last snapshot date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output parquet file path (default: data/training_dataset_<dates>.parquet)",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Restrict to a single user ID",
    )
    parser.add_argument(
        "--min-history-days",
        type=int,
        default=2,
        help="Minimum days of user history before snapshot (default: 2)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50000,
        help="Rows per progress batch (default: 50000)",
    )
    parser.add_argument(
        "--sample",
        type=float,
        default=None,
        help="Sample fraction (0.0-1.0) for testing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    print(f"Environment: {settings.environment}")
    print(f"Connecting to database...")

    session_factory = get_session_factory()
    db: Session = session_factory()

    try:
        from_date = date_from_iso(args.from_date)
        to_date = date_from_iso(args.to_date)
        if from_date is None or to_date is None:
            print("ERROR: Invalid date range")
            return 1
        if from_date >= to_date:
            print("ERROR: from-date must be before to-date")
            return 1

        print(f"\n=== ML Dataset Builder (Phase 2) ===")
        print(f"Snapshot range: {from_date} to {to_date}")
        if args.user_id:
            print(f"Restricted to user: {args.user_id}")

        t0 = time.time()
        df = build_dataset(
            db,
            from_date,
            to_date,
            user_id=args.user_id,
            min_history_days=args.min_history_days,
            batch_size=args.batch_size,
        )
        elapsed = time.time() - t0

        if df.empty:
            print("No rows generated. Exiting.")
            return 0

        # Sample if requested
        if args.sample is not None:
            df = df.sample(frac=min(args.sample, 1.0), random_state=42)
            print(f"Sampled: {len(df)} rows (fraction={args.sample})")

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"training_dataset_{from_date}_to_{to_date}.parquet"
            output_path = OUTPUT_DIR / fname

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write parquet
        print(f"\nWriting {len(df)} rows to {output_path}...")
        # Drop the debug column before saving
        df_for_export = df.drop(columns=["task_title_hint"], errors="ignore")
        df_for_export.to_parquet(
            str(output_path),
            index=False,
            compression="zstd",
            row_group_size=10000,
        )

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"Done in {elapsed:.1f}s — file size: {file_size_mb:.1f} MB")

        # Quick stats
        print(f"\n=== Quick Stats ===")
        print(f"Total rows: {len(df):,}")
        pos = df["label"].sum()
        neg = len(df) - pos
        print(f"Positive labels: {pos:,} ({pos/max(len(df),1)*100:.1f}%)")
        print(f"Negative labels: {neg:,} ({neg/max(len(df),1)*100:.1f}%)")
        print(f"Columns ({len(df.columns)}): {', '.join(sorted(df.columns))}")

        # Feature null summary
        null_cols = df.columns[df.isnull().any()].tolist()
        if null_cols:
            print(f"\n⚠️  Columns with null values: {null_cols}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    raise SystemExit(main())
