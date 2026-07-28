"""
Phase 5: ML Prediction Service — Next-Day Task Scoring
========================================================

Provides the MLPredictionService class that:
  - Loads the trained model pipeline from disk (lazy, cached)
  - Computes the same 38 features used during training
  - Scores candidate tasks for tomorrow's plan
  - Falls back gracefully on any error (model missing, corrupt, etc.)

Usage:
    service = MLPredictionService()
    scores = service.predict(tasks, db, user_id, snapshot_date, timezone_str)
    # -> {"task_id_1": 0.85, "task_id_2": 0.32}

Integration target:
    DailyPlanService._list_candidate_tasks() — after getting tasks, call
    MLPredictionService.predict() to re-rank by ML score.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sqlalchemy import text as sqltext
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

__all__ = ["MLPredictionService", "compute_end_of_day"]

# ---------------------------------------------------------------------------
# Path setup — find model artifacts relative to the backend root
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MODEL_DIR = _BACKEND_ROOT / "models" / "synthetic"
_DEFAULT_MODEL_PATH = _DEFAULT_MODEL_DIR / "model_pipeline.joblib"
_DEFAULT_FEATURES_PATH = _DEFAULT_MODEL_DIR / "feature_groups.json"
_DEFAULT_METADATA_PATH = _DEFAULT_MODEL_DIR / "metadata.json"

# Constants replicated from build_ml_dataset.py for self-contained inference
_MAX_SAFE_INT = 9999
_DEFAULT_ESTIMATED_DURATION = 30
_DEFAULT_LOOKBACK_DAYS = 7

# Confidence bands for product decisions
_CONFIDENCE_HIGH = 0.70   # score >= 0.70 -> auto-include
_CONFIDENCE_MEDIUM = 0.40  # score >= 0.40 -> suggest

_TIMEZONE_CACHE: dict[str, ZoneInfo] = {}


# ---------------------------------------------------------------------------
# TIMEZONE helpers (same logic as build_ml_dataset.py)
# ---------------------------------------------------------------------------


def _get_tz(tz_name: str) -> ZoneInfo:
    if tz_name not in _TIMEZONE_CACHE:
        _TIMEZONE_CACHE[tz_name] = ZoneInfo(tz_name)
    return _TIMEZONE_CACHE[tz_name]


def compute_end_of_day(d: date, timezone_str: str) -> datetime:
    """Return end of calendar day D in user's timezone, as UTC datetime."""
    tz = _get_tz(timezone_str)
    end_local = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=tz)
    return end_local.astimezone(UTC)


def _ensure_dt(val: Any) -> datetime | Any:
    """Normalize string datetime (SQLite) to proper datetime object."""
    if isinstance(val, str):
        try:
            val = val.replace("T", " ")[:26]
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=UTC)
        except (ValueError, TypeError):
            try:
                return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            except (ValueError, TypeError):
                pass
    return val


def _parse_json_list(val: Any) -> list[str]:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def date_from_iso(s: str | None) -> date | None:
    if s is None:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# DB query helpers (pulled from build_ml_dataset.py for feature computation)
# ---------------------------------------------------------------------------

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
    """Reconstruct task statuses at end_of_d for ALL tasks (single query)."""
    if not task_ids:
        return {}

    quoted = [f"'{tid}'" for tid in task_ids]
    in_clause = ", ".join(quoted)

    rows = db.execute(
        sqltext(
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
        ),
        {"uid": user_id, "end_of_d": end_of_d},
    ).fetchall()

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
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
) -> dict[str, dict[str, int]]:
    """Get event counts for ALL tasks in one query."""
    if not task_ids:
        return {}

    lookback_start = end_of_d - timedelta(days=lookback_days)
    quoted = [f"'{tid}'" for tid in task_ids]
    in_clause = ", ".join(quoted)

    rows = db.execute(
        sqltext(
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
        ),
        {
            "uid": user_id,
            "lookback_start": lookback_start,
            "end_of_d": end_of_d,
        },
    ).fetchall()

    result: dict[str, dict[str, int]] = {
        tid: {
            "completion_count_7d": 0,
            "deferral_count_7d": 0,
            "move_count_7d": 0,
            "skip_count_7d": 0,
            "update_count_7d": 0,
            "days_since_last_completion": _MAX_SAFE_INT,
        }
        for tid in task_ids
    }

    for entity_id, event_type, occurred_at in rows:
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
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
) -> dict[str, Any]:
    """Compute user-level context features (single aggregate query)."""
    lookback_start = end_of_d - timedelta(days=lookback_days)
    lookback_date_str = (snapshot_date - timedelta(days=lookback_days)).isoformat()
    target_date_str = target_date.isoformat()

    row = db.execute(
        sqltext(
            """
            SELECT
                (SELECT COUNT(*) FROM tasks
                 WHERE user_id = :uid
                   AND (deleted_at IS NULL OR deleted_at > :end_of_d)
                   AND (completed_at IS NULL OR completed_at > :end_of_d)
                   AND created_at <= :end_of_d
                ) AS total_open,

                (SELECT COUNT(*) FROM tasks
                 WHERE user_id = :uid
                   AND task_type = 'scheduled'
                   AND (deleted_at IS NULL OR deleted_at > :end_of_d)
                   AND (completed_at IS NULL OR completed_at > :end_of_d)
                   AND created_at <= :end_of_d
                ) AS scheduled_count,

                (SELECT COUNT(*) FROM tasks
                 WHERE user_id = :uid
                   AND task_type = 'flexible'
                   AND (deleted_at IS NULL OR deleted_at > :end_of_d)
                   AND (completed_at IS NULL OR completed_at > :end_of_d)
                   AND created_at <= :end_of_d
                ) AS flexible_count,

                (SELECT COUNT(DISTINCT t.id) FROM tasks t
                 JOIN daily_plans dp ON dp.id = t.daily_plan_id
                 WHERE t.user_id = :uid
                   AND (t.deleted_at IS NULL OR t.deleted_at > :end_of_d)
                   AND dp.plan_date >= :lookback_date_str
                   AND dp.plan_date < :target_date_str
                ) AS planned_in_window,

                (SELECT COUNT(DISTINCT entity_id) FROM activity_events
                 WHERE user_id = :uid
                   AND entity_type = 'task'
                   AND event_type = 'task_completed'
                   AND occurred_at > :lookback_start
                   AND occurred_at <= :end_of_d
                ) AS completed_in_window,

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

    completion_rate = (
        completed_in_window / planned_in_window
        if planned_in_window > 0
        else 0.5
    )

    days_since_last_plan = _MAX_SAFE_INT
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


def _get_preferences(db: Session, user_id: str) -> dict[str, Any]:
    """Get user schedule preferences (single query)."""
    row = db.execute(
        sqltext(
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
# Feature computation (replicates build_ml_dataset.py logic)
# ---------------------------------------------------------------------------


def _compute_task_features_dict(
    task_id: str,
    created_at: datetime,
    deadline: str | None,
    estimated_duration: int | None,
    task_type: str,
    priority: str | None,
    tags: list[str],
    description: str | None,
    snapshot_date: date,
) -> dict[str, Any]:
    """Compute task-level features (same as _compute_task_features in build_ml_dataset).

    Note: ``end_of_d``, present in the build_ml_dataset version, is omitted here
    because task-level features only need ``snapshot_date`` for relative calculations.
    """
    features: dict[str, Any] = {}

    # Ensure datetime is timezone-aware UTC for date comparison
    if created_at.tzinfo is not None:
        created_at_utc = created_at.astimezone(UTC).replace(tzinfo=None)
    else:
        created_at_utc = created_at

    # Task age at snapshot
    features["task_age_days"] = max(0, (snapshot_date - created_at_utc.date()).days)

    # Deadline features
    dl = date_from_iso(deadline)
    features["has_deadline"] = dl is not None
    features["is_overdue"] = bool(dl and dl < snapshot_date)
    if dl:
        features["deadline_relative_days"] = (dl - snapshot_date).days
    else:
        features["deadline_relative_days"] = _MAX_SAFE_INT

    # Estimated duration
    dur = estimated_duration
    features["estimated_duration"] = dur if dur is not None else _DEFAULT_ESTIMATED_DURATION
    features["has_estimated_duration"] = dur is not None

    # Priority (one-hot)
    pri = (priority or "normal").lower()
    features["priority_urgent"] = pri == "urgent"
    features["priority_high"] = pri == "high"
    features["priority_normal"] = pri == "normal"
    features["priority_low"] = pri == "low"

    # Task type
    ttype = task_type or "scheduled"
    features["task_type_scheduled"] = ttype == "scheduled"
    features["task_type_flexible"] = ttype == "flexible"

    # Tags
    features["num_tags"] = len(tags or [])

    # Description
    has_desc = bool(description)
    features["has_description"] = has_desc
    features["description_length"] = len(description) if has_desc else 0

    return features


def _get_temporal_features(target_date: date, is_day_off: bool) -> dict[str, Any]:
    """Compute temporal features (same as _get_temporal_features in build_ml_dataset)."""
    dow = target_date.weekday()
    return {
        "target_day_of_week": dow,
        "target_is_monday": dow == 0,
        "target_is_friday": dow == 4,
        "target_is_weekend": dow >= 5,
        "target_is_day_off": is_day_off,
    }


# ---------------------------------------------------------------------------
# Staging strategy → model directory mapping
# ---------------------------------------------------------------------------

_STRATEGY_MODEL_DIRS: dict[str, Path] = {
    "synthetic": _BACKEND_ROOT / "models" / "synthetic",
    "retrained": _BACKEND_ROOT / "models" / "retrained",
}


def _resolve_strategy(
    strategy: str | None,
) -> tuple[Path, Path, Path]:
    """Resolve a strategy name to (model_dir, model_path, metadata_path).

    Falls back to synthetic if the requested strategy's model dir is missing.
    """
    if strategy is None:
        strategy = "synthetic"

    model_dir = _STRATEGY_MODEL_DIRS.get(strategy)
    if model_dir is None:
        logger.warning("Unknown ML strategy %r — falling back to synthetic", strategy)
        model_dir = _STRATEGY_MODEL_DIRS["synthetic"]

    # If the requested strategy's model dir doesn't exist, fall back
    if not model_dir.exists():
        logger.warning(
            "ML strategy %r directory %s not found — falling back to synthetic",
            strategy, model_dir,
        )
        model_dir = _STRATEGY_MODEL_DIRS["synthetic"]

    return (
        model_dir,
        model_dir / "model_pipeline.joblib",
        model_dir / "metadata.json",
    )


# ---------------------------------------------------------------------------
# Feature groups (known from training artifact)
# ---------------------------------------------------------------------------

# These must match feature_groups.json from the trained model.
# Loaded dynamically from disk; this is the fallback if file is missing.
_FALLBACK_FEATURE_GROUPS = {
    "numeric": [
        "days_since_last_completion",
        "deadline_relative_days",
        "description_length",
        "estimated_duration",
        "target_day_of_week",
        "task_age_days",
        "user_completed_count_7d",
        "user_completion_rate_7d",
        "user_flexible_count",
        "user_planned_count_7d",
        "user_scheduled_count",
        "user_total_open_tasks",
    ],
    "categorical": ["status_at_d"],
    "binary": [
        "completion_count_7d",
        "days_since_last_plan",
        "deferral_count_7d",
        "has_deadline",
        "has_description",
        "has_estimated_duration",
        "has_plan_for_past_or_today",
        "is_overdue",
        "move_count_7d",
        "num_tags",
        "priority_high",
        "priority_low",
        "priority_normal",
        "priority_urgent",
        "skip_count_7d",
        "status_is_deferred",
        "status_is_planned",
        "status_is_skipped",
        "target_is_day_off",
        "target_is_friday",
        "target_is_monday",
        "target_is_weekend",
        "task_type_flexible",
        "task_type_scheduled",
        "update_count_7d",
    ],
}


# ---------------------------------------------------------------------------
# Model artifact loader
# ---------------------------------------------------------------------------


def _load_feature_groups(path: Path | None = None) -> dict[str, list[str]]:
    """Load feature groups from JSON, with fallback to hardcoded defaults."""
    if path is None:
        path = _DEFAULT_FEATURES_PATH
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load feature_groups.json from %s: %s", path, exc)
    logger.info("Using fallback feature groups (hardcoded defaults)")
    return dict(_FALLBACK_FEATURE_GROUPS)


# ---------------------------------------------------------------------------
# MLPredictionService
# ---------------------------------------------------------------------------


@dataclass
class MLPredictionService:
    """Service that scores candidate tasks using the trained ML model.

    The model is loaded lazily on the first call to ``predict()``.
    All failure modes (missing file, corrupt model, DB error, etc.) are
    caught and trigger a graceful fallback returning an empty dict.

    Thread-safe after initialization because model loading is write-once
    and subsequent calls are read-only.
    """

    model_path: str | Path = field(default_factory=lambda: _DEFAULT_MODEL_PATH)
    feature_groups_path: str | Path | None = None
    strategy: str = ""

    # Lazy-loaded state (populated on first predict call)
    _pipeline: Any = None
    _feature_groups: dict[str, list[str]] | None = None
    _model_type: str = ""
    _model_version: str = ""
    _loaded: bool = False
    _load_error: str = ""
    _metadata_path: str | Path | None = None

    def __post_init__(self) -> None:
        # If a strategy was provided, resolve paths from it (unless explicit paths given)
        if self.strategy and self.model_path == _DEFAULT_MODEL_PATH and self.feature_groups_path is None:
            model_dir, model_path, meta_path = _resolve_strategy(self.strategy)
            self.model_path = model_path
            self._metadata_path = meta_path
            self.feature_groups_path = model_dir / "feature_groups.json"
        else:
            self.model_path = Path(self.model_path)
            if self.feature_groups_path is not None:
                self.feature_groups_path = Path(self.feature_groups_path)
            if self._metadata_path is not None:
                self._metadata_path = Path(self._metadata_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        tasks: list[Any],
        db: Session,
        user_id: str,
        snapshot_date: date | None = None,
        timezone_str: str | None = None,
    ) -> dict[str, float]:
        """Score candidate tasks for tomorrow's plan.

        Args:
            tasks: List of SQLAlchemy Task objects (or dicts with matching keys).
            db: Active DB session for feature queries.
            user_id: User ID string.
            snapshot_date: Snapshot date (defaults to today UTC).
            timezone_str: User timezone (defaults to Asia/Saigon).

        Returns:
            Dict of {task_id: ml_score} in [0, 1].
            Returns empty dict on any error (graceful fallback).
        """
        # --- Guard: empty input ---
        if not tasks:
            logger.debug("ML predict called with empty tasks list — skipping")
            return {}

        # --- Ensure model is loaded ---
        if not self._ensure_model_loaded():
            logger.warning("ML model not available (reason: %s) — falling back", self._load_error)
            return {}

        # --- Defaults ---
        if snapshot_date is None:
            snapshot_date = datetime.now(UTC).date()
        timezone_str = timezone_str or "Asia/Saigon"
        target_date = snapshot_date + timedelta(days=1)
        end_of_d = compute_end_of_day(snapshot_date, timezone_str)

        t0 = time.time()

        try:
            # --- Extract task IDs and normalize tasks to dicts ---
            task_dicts, task_ids = self._normalize_tasks(tasks)
            if not task_ids:
                return {}

            # --- Batch queries ---
            prefs = _get_preferences(db, user_id)
            day_offs = prefs.get("day_offs", [])
            weekday_name = target_date.strftime("%A")
            is_day_off = weekday_name in day_offs

            status_map = _batch_reconstruct_statuses(db, user_id, task_ids, end_of_d)
            event_counts = _batch_get_event_counts(db, user_id, task_ids, end_of_d)
            user_context = _get_user_context_features(
                db, user_id, end_of_d, timezone_str, target_date, snapshot_date,
            )
            temporal_feats = _get_temporal_features(target_date, is_day_off)

            # --- Build feature vectors ---
            rows: list[dict[str, Any]] = []
            for task_dict in task_dicts:
                tid = task_dict["id"]

                # Task-level features
                task_feats = _compute_task_features_dict(
                    task_id=tid,
                    created_at=task_dict["created_at"],
                    deadline=task_dict.get("deadline"),
                    estimated_duration=task_dict.get("estimated_duration"),
                    task_type=task_dict.get("task_type", "scheduled"),
                    priority=task_dict.get("priority", "normal"),
                    tags=task_dict.get("tags", []),
                    description=task_dict.get("description"),
                    snapshot_date=snapshot_date,
                )

                # Status at D (from batch query)
                status_at_d = status_map.get(tid, "todo")
                task_feats["status_at_d"] = status_at_d
                task_feats["status_is_planned"] = status_at_d == "planned"
                task_feats["status_is_deferred"] = status_at_d == "deferred"
                task_feats["status_is_skipped"] = status_at_d == "skipped"

                # Has plan for past or today
                task_feats["has_plan_for_past_or_today"] = bool(
                    task_dict.get("daily_plan_id")
                )

                # Event counts (from batch query)
                ev = event_counts.get(tid, {})
                task_feats["completion_count_7d"] = ev.get("completion_count_7d", 0)
                task_feats["deferral_count_7d"] = ev.get("deferral_count_7d", 0)
                task_feats["move_count_7d"] = ev.get("move_count_7d", 0)
                task_feats["skip_count_7d"] = ev.get("skip_count_7d", 0)
                task_feats["update_count_7d"] = ev.get("update_count_7d", 0)
                task_feats["days_since_last_completion"] = ev.get("days_since_last_completion", _MAX_SAFE_INT)

                # User context (same for all tasks)
                task_feats.update(user_context)

                # Temporal (same for all tasks)
                task_feats.update(temporal_feats)

                # Store task_id for final mapping
                task_feats["_task_id"] = tid
                rows.append(task_feats)

            if not rows:
                return {}

            # --- Build DataFrame with exactly the expected feature columns ---
            feature_cols = (
                self._feature_groups["numeric"]
                + self._feature_groups["categorical"]
                + self._feature_groups["binary"]
            )
            df = pd.DataFrame(rows)

            # Ensure all expected columns exist (fill missing with 0)
            for col in feature_cols:
                if col not in df.columns:
                    df[col] = 0

            # Select only the expected columns (in the right order)
            X = df[feature_cols].copy()

            # Handle any NaN values (shouldn't happen, but be safe)
            X = X.fillna(0)

            # --- Predict ---
            proba = self._pipeline.predict_proba(X)
            if proba.shape[1] >= 2:
                scores = proba[:, 1]
            else:
                scores = np.zeros(len(proba))

            # --- Build result ---
            task_ids_arr = df["_task_id"].values
            result = {str(tid): round(float(score), 4) for tid, score in zip(task_ids_arr, scores)}

            elapsed = time.time() - t0
            logger.debug(
                "ML predict: %d tasks scored in %.3fs (model=%s)",
                len(result), elapsed, self._model_type,
            )

            return result

        except Exception as exc:
            elapsed = time.time() - t0
            logger.warning(
                "ML prediction failed after %.3fs: %s — falling back",
                elapsed, exc,
            )
            return {}

    @property
    def model_version(self) -> str:
        """Return the model version string (from metadata.json timestamp)."""
        return self._model_version

    @property
    def model_metadata(self) -> dict[str, Any]:
        """Return the full model metadata dict (loaded from metadata.json)."""
        md_path = self._metadata_path or _DEFAULT_METADATA_PATH
        if md_path.exists():
            try:
                with open(md_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"model_type": self._model_type, "version": self._model_version}

    def log_predictions(
        self,
        db: Session,
        plan_id: str,
        user_id: str,
        result: "PredictionResult",
    ) -> None:
        """Bulk-log prediction results to ``MLPredictionLog`` for monitoring.

        This is called from ``DailyPlanService`` after ``predict_result()``.
        Logging is best-effort: errors are logged and swallowed.
        """
        from src.db.models import MLPredictionLog

        if not result or not result.predictions:
            return

        try:
            rows = [
                MLPredictionLog(
                    user_id=user_id,
                    plan_id=plan_id,
                    task_id=pred.task_id,
                    prediction_score=pred.score,
                    confidence_band=pred.confidence_band,
                    model_version=self._model_version or "unknown",
                    model_type=self._model_type or "unknown",
                    outcome="pending",
                )
                for pred in result.predictions
            ]
            db.add_all(rows)
            # No flush here — caller (DailyPlanService) will commit all changes
            # together, which handles FK dependency ordering automatically.
            logger.debug("Logged %d ML predictions for plan %s", len(rows), plan_id)
        except Exception as exc:
            logger.warning("Failed to log ML predictions: %s", exc, exc_info=True)

    def predict_result(
        self,
        tasks: list[Any],
        db: Session,
        user_id: str,
        snapshot_date: date | None = None,
        timezone_str: str | None = None,
    ) -> "PredictionResult":
        """Like ``predict()`` but returns a structured ``PredictionResult``.

        This is the preferred interface for integration because it includes
        metadata about the inference status.
        """
        from src.modules.ml.schemas import PredictionResult, TaskPrediction

        scores = self.predict(tasks, db, user_id, snapshot_date, timezone_str)

        if not scores:
            if not tasks:
                return PredictionResult(
                    result_status="fallback_empty_input",
                    classifier_type=self._model_type,
                    n_candidates=0,
                    n_scored=0,
                    fallback_used=True,
                )
            return PredictionResult(
                result_status="fallback_prediction_error",
                classifier_type=self._model_type,
                n_candidates=len(tasks),
                n_scored=0,
                fallback_used=True,
            )

        predictions = []
        n_high = 0
        n_medium = 0
        for tid, score in scores.items():
            if score >= _CONFIDENCE_HIGH:
                band = "high"
                n_high += 1
            elif score >= _CONFIDENCE_MEDIUM:
                band = "medium"
                n_medium += 1
            else:
                band = "low"
            predictions.append(TaskPrediction(
                task_id=tid,
                score=score,
                confidence_band=band,
            ))

        result_status = "ok"
        fallback_used = False
        if not self._loaded:
            result_status = "fallback_model_missing"
            fallback_used = True

        # Re-read model_version from metadata if not already set
        if not self._model_version:
            md = self.model_metadata
            self._model_version = md.get("timestamp", md.get("version", "unknown"))

        return PredictionResult(
            predictions=predictions,
            result_status=result_status,
            classifier_type=self._model_type,
            n_candidates=len(tasks),
            n_scored=len(scores),
            n_high_confidence=n_high,
            n_medium_confidence=n_medium,
            fallback_used=fallback_used,
        )

    def get_confidence_bands(self) -> dict[str, float]:
        """Return the confidence band thresholds used by this service."""
        return {
            "high": _CONFIDENCE_HIGH,
            "medium": _CONFIDENCE_MEDIUM,
        }

    def is_available(self) -> bool:
        """Check whether the model is loaded and ready."""
        return self._loaded

    def reload(self) -> bool:
        """Force-reload the model from disk. Useful after model update."""
        self._pipeline = None
        self._feature_groups = None
        self._model_type = ""
        self._model_version = ""
        self._loaded = False
        self._load_error = ""
        return self._ensure_model_loaded()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_model_loaded(self) -> bool:
        """Lazy-load model and feature groups on first use."""
        if self._loaded:
            return True
        return self._load_model()

    def _load_model(self) -> bool:
        """Attempt to load the model pipeline and feature groups from disk."""
        import joblib

        # --- Load feature groups ---
        try:
            self._feature_groups = _load_feature_groups(self.feature_groups_path)
        except Exception as exc:
            logger.warning("Failed to load feature groups: %s", exc)
            self._load_error = f"feature_groups: {exc}"
            return False

        # --- Check model file exists ---
        if not self.model_path.exists():
            logger.warning("ML model not found at %s — inference disabled", self.model_path)
            self._load_error = f"model file not found: {self.model_path}"
            return False

        # --- Load model ---
        try:
            pipeline = joblib.load(str(self.model_path))
            # Validate structure
            if not hasattr(pipeline, "predict_proba"):
                raise ValueError("Loaded object has no predict_proba method")
            self._pipeline = pipeline
            self._model_type = type(pipeline[-1]).__name__
            self._loaded = True
            logger.info(
                "ML model loaded: %s (%.1f KB, %s)",
                self.model_path,
                self.model_path.stat().st_size / 1024,
                self._model_type,
            )
            return True
        except Exception as exc:
            self._pipeline = None
            self._load_error = f"model load failed: {exc}"
            logger.warning("Failed to load ML model from %s: %s", self.model_path, exc)
            return False

    @staticmethod
    def _normalize_tasks(tasks: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
        """Normalize tasks to dicts, handling both SQLAlchemy models and dicts."""
        task_dicts: list[dict[str, Any]] = []
        for task in tasks:
            if hasattr(task, "_sa_instance_state"):
                # SQLAlchemy model -> dict
                d = {
                    "id": task.id,
                    "created_at": task.created_at,
                    "deadline": task.deadline,
                    "estimated_duration": task.estimated_duration,
                    "task_type": task.task_type,
                    "priority": task.priority,
                    "tags": getattr(task, "tags", []),
                    "description": task.description,
                    "daily_plan_id": task.daily_plan_id,
                    "title": task.title,
                    "status": task.status,
                }
            elif isinstance(task, dict):
                d = task
            else:
                continue
            task_dicts.append(d)

        task_ids = [d["id"] for d in task_dicts if d.get("id")]
        return task_dicts, task_ids
