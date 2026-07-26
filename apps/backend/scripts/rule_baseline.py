"""
Phase 4: Rule-Based Baseline Comparison
=========================================

Implements a simple rule-based scorer for next-day task prediction and
compares it against the ML baseline (weighted LogisticRegression).

Rule-based scoring uses heuristics that mimic how a product manager might
manually prioritize tasks:
  1. Deadline urgency: overdue > closer deadline > no deadline
  2. Priority: urgent > high > normal > low
  3. Recent planning history: tasks recently planned are more likely
  4. Activity momentum: recently completed/deferred tasks are active
  5. Task type: scheduled > flexible
  6. Temporal adjustment: day-of-week factors

Usage:
    python scripts/rule_baseline.py \\
        --dataset data/full_training_dataset.parquet \\
        --output-dir models/ \\
        --train-snapshots 14
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Reuse infrastructure from train_baseline
# ---------------------------------------------------------------------------

from scripts.train_baseline import (
    META_COLUMNS,
    TARGET_COLUMN,
    _compute_metrics,
    _identify_feature_columns,
    _time_based_split,
    train_pipeline,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Weights for each heuristic component (sum does not need to = 1)
WEIGHTS = {
    "deadline_urgency": 3.0,
    "priority": 2.0,
    "recent_planning": 1.5,
    "activity_momentum": 1.0,
    "task_type": 0.5,
    "temporal": 0.5,
}


# ---------------------------------------------------------------------------
# Scoring functions (one per heuristic)
# ---------------------------------------------------------------------------


def _score_deadline_urgency(row: dict[str, Any]) -> float:
    """Score based on deadline proximity.

    Returns 0.0 to 1.0:
      - 1.0 if overdue (deadline already passed)
      - 1.0 if deadline is today (relative_days == 0)
      - decays as relative_days increases: 0.9 / (1 + relative_days)
      - 0.2 if no deadline set
    """
    # Check overdue first (implies a deadline exists even if has_deadline is stale)
    if row.get("is_overdue", False):
        return 1.0

    rel_days = row.get("deadline_relative_days", 9999)

    # Negative rel_days means the deadline is in the past (also overdue)
    if rel_days < 0:
        return 1.0

    # No deadline set
    if not row.get("has_deadline", False):
        return 0.2

    # Sentinel for missing deadline data
    if rel_days == 9999:
        return 0.2

    # Deadline is today
    if rel_days <= 0:
        return 1.0

    # Decay: 0.9 / (1 + rel_days)
    return round(0.9 / (1.0 + rel_days), 4)


def _score_priority(row: dict[str, Any]) -> float:
    """Score based on task priority.

    Returns:
      - 1.0 if urgent
      - 0.8 if high
      - 0.5 if normal (default)
      - 0.2 if low
    """
    if row.get("priority_urgent", False):
        return 1.0
    if row.get("priority_high", False):
        return 0.8
    if row.get("priority_low", False):
        return 0.2
    return 0.5  # normal (default)


def _score_recent_planning(row: dict[str, Any]) -> float:
    """Score based on how recently the task was planned.

    Returns 0.0 to 1.0:
      - 0.8 if already planned for today or past (has_plan_for_past_or_today)
      - otherwise decays with days_since_last_plan
      - 0.0 if never planned
    """
    if row.get("has_plan_for_past_or_today", False):
        return 0.8

    days = row.get("days_since_last_plan", 9999)
    if days == 9999:
        return 0.0  # never planned

    # Recently planned → higher score (decay: 0.7 / (1 + days))
    return round(0.7 / (1.0 + days), 4)


def _score_activity_momentum(row: dict[str, Any]) -> float:
    """Score based on recent activity (completions, history).

    Returns 0.0 to 1.0:
      - Higher completion_count_7d → higher score (capped at 5 events)
      - Captures tasks that are actively being worked on
    """
    n_completions = min(row.get("completion_count_7d", 0), 5)
    n_deferrals = min(row.get("deferral_count_7d", 0), 3)

    # Base from completions (0-5 completions → 0-0.6)
    comp_score = n_completions * 0.12
    # Bonus from deferrals (indicates the task was actively considered)
    defer_score = n_deferrals * 0.05

    return round(min(comp_score + defer_score, 1.0), 4)


def _score_task_type(row: dict[str, Any]) -> float:
    """Score based on task type.

    Returns:
      - 0.7 for scheduled
      - 0.3 for flexible
    """
    if row.get("task_type_scheduled", False):
        return 0.7
    return 0.3  # flexible or unknown


def _score_temporal(row: dict[str, Any]) -> float:
    """Score based on day-of-week factors.

    Returns 0.0 to 1.0 (adjustment, usually near 0.5):
      - Higher on Mondays (planning day)
      - Lower on weekends (rest days)
      - Lower if target is a day-off
    """
    score = 0.5  # neutral

    # Higher on Mondays (fresh week)
    if row.get("target_is_monday", False):
        score += 0.2
    # Higher on Fridays (wrap up)
    if row.get("target_is_friday", False):
        score += 0.1
    # Lower on weekends
    if row.get("target_is_weekend", False):
        score -= 0.2
    # Lower if it's a day off
    if row.get("target_is_day_off", False):
        score -= 0.15

    return round(max(0.0, min(score, 1.0)), 4)


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------


def rule_score(row: dict[str, Any]) -> float:
    """Compute the combined rule-based score for a candidate task.

    Combines all heuristics with weighted sum, normalized to [0, 1].
    """
    scores = {
        "deadline": _score_deadline_urgency(row),
        "priority": _score_priority(row),
        "planning": _score_recent_planning(row),
        "momentum": _score_activity_momentum(row),
        "type": _score_task_type(row),
        "temporal": _score_temporal(row),
    }

    weighted = (
        scores["deadline"] * WEIGHTS["deadline_urgency"]
        + scores["priority"] * WEIGHTS["priority"]
        + scores["planning"] * WEIGHTS["recent_planning"]
        + scores["momentum"] * WEIGHTS["activity_momentum"]
        + scores["type"] * WEIGHTS["task_type"]
        + scores["temporal"] * WEIGHTS["temporal"]
    )

    total_weight = sum(WEIGHTS.values())
    return round(weighted / total_weight, 4)


def compute_rule_scores(df: pd.DataFrame) -> np.ndarray:
    """Compute rule-based scores for all rows in a DataFrame.

    Returns:
        numpy array of scores in [0, 1], one per row.
    """
    records = df.to_dict(orient="records")
    scores = np.array([rule_score(r) for r in records], dtype=float)
    return scores


# ---------------------------------------------------------------------------
# Comparison runner
# ---------------------------------------------------------------------------


def _score_breakdown(row: dict[str, Any]) -> dict[str, float]:
    """Return the individual component scores for a single row."""
    return {
        "deadline_urgency": _score_deadline_urgency(row),
        "priority": _score_priority(row),
        "recent_planning": _score_recent_planning(row),
        "activity_momentum": _score_activity_momentum(row),
        "task_type": _score_task_type(row),
        "temporal": _score_temporal(row),
        "combined": rule_score(row),
    }


def _format_comparison_table(
    ml_metrics: dict[str, Any],
    rule_metrics: dict[str, Any],
) -> str:
    """Format a side-by-side comparison table as a string."""
    lines = [
        "=" * 70,
        "ML vs RULE-BASED BASELINE COMPARISON",
        "=" * 70,
        f"{'Metric':<30s} {'ML (LogisticRegression)':>18s} {'Rule-Based':>18s}",
        "-" * 70,
    ]

    # Standard metrics
    for key in ["precision", "recall", "f1", "roc_auc", "average_precision"]:
        ml_val = ml_metrics.get(key)
        rule_val = rule_metrics.get(key)
        ml_str = f"{ml_val:.4f}" if ml_val is not None else "N/A"
        rule_str = f"{rule_val:.4f}" if rule_val is not None else "N/A"
        lines.append(f"{key:<30s} {ml_str:>18s} {rule_str:>18s}")

    # Top-k metrics
    lines.append("")
    lines.append(f"{'--- Top-k ---':<30s}")
    all_ks = sorted(
        set(ml_metrics.get("top_k", {}).keys())
        | set(rule_metrics.get("top_k", {}).keys())
    )
    for k in all_ks:
        ml_val = ml_metrics.get("top_k", {}).get(k)
        rule_val = rule_metrics.get("top_k", {}).get(k)
        ml_str = f"{ml_val:.4f}" if ml_val is not None else "N/A"
        rule_str = f"{rule_val:.4f}" if rule_val is not None else "N/A"
        lines.append(f"{k:<30s} {ml_str:>18s} {rule_str:>18s}")

    # Label distribution
    lines.append("")
    lines.append(f"Validation set: {ml_metrics.get('n_total', '?')} rows")
    lines.append(
        f"  Positive labels: {ml_metrics.get('n_positive', '?')} "
        f"({ml_metrics.get('positive_ratio', 0) * 100:.1f}%)"
    )

    lines.append("=" * 70)
    return "\n".join(lines)


def run_comparison(
    df: pd.DataFrame,
    *,
    output_dir: str | Path = "models/",
    train_snapshots: int = 14,
) -> dict[str, Any]:
    """Run both ML and rule-based baselines and compare.

    Args:
        df: Full training dataset
        output_dir: Directory to save comparison report
        train_snapshots: Number of earliest snapshots for training

    Returns:
        dict with 'ml_metrics', 'rule_metrics', and 'comparison_summary'
    """
    output_path = Path(output_dir) if not isinstance(output_dir, Path) else output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # --- Split (same for both) ---
    train_df, val_df = _time_based_split(df, train_snapshots=train_snapshots)
    print(f"Split: {len(train_df)} train / {len(val_df)} validation rows")

    # --- 1. ML baseline ---
    print("\n=== Training ML Baseline ===")
    t0 = time.time()
    ml_metrics = train_pipeline(
        df,
        output_dir=str(output_path),
        train_snapshots=train_snapshots,
    )
    ml_time = time.time() - t0
    print(f"ML training time: {ml_time:.2f}s")

    # --- 2. Rule-based baseline ---
    print("\n=== Computing Rule-Based Scores ===")
    t0 = time.time()
    # Re-split to get the same val_df
    _, val_df_reuse = _time_based_split(df, train_snapshots=train_snapshots)

    # Identify feature columns (same as ML)
    col_groups = _identify_feature_columns(df)
    feature_cols = (
        col_groups["numeric"] + col_groups["categorical"] + col_groups["binary"]
    )
    available = set(df.columns)
    feature_cols = [c for c in feature_cols if c in available]

    # Compute rule scores
    rule_scores_val = compute_rule_scores(val_df_reuse)
    rule_metrics = _compute_metrics(
        val_df_reuse[TARGET_COLUMN].values,
        rule_scores_val,
    )
    rule_metrics["model_type"] = "RuleBased"
    rule_time = time.time() - t0
    print(f"Rule scoring time: {rule_time:.4f}s")

    # --- 3. Comparison ---
    print(f"\n{_format_comparison_table(ml_metrics, rule_metrics)}")

    # --- 4. Save comparison report ---
    report = {
        "ml": {
            "metrics": {k: v for k, v in ml_metrics.items() if k != "top_k"},
            "top_k": ml_metrics.get("top_k", {}),
            "training_time_s": round(ml_time, 3),
        },
        "rule_based": {
            "metrics": {k: v for k, v in rule_metrics.items() if k != "top_k"},
            "top_k": rule_metrics.get("top_k", {}),
            "scoring_time_s": round(rule_time, 4),
        },
        "comparison": {
            "winner": _determine_winner(ml_metrics, rule_metrics),
            "n_train": len(train_df),
            "n_val": len(val_df),
            "positive_ratio_val": round(
                val_df[TARGET_COLUMN].sum() / max(len(val_df), 1), 4
            ),
            "rule_weights": WEIGHTS,
        },
    }

    report_path = output_path / "comparison_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nComparison report saved: {report_path}")

    return {
        "ml_metrics": ml_metrics,
        "rule_metrics": rule_metrics,
        "comparison_summary": report["comparison"],
    }


def _determine_winner(
    ml_metrics: dict[str, Any],
    rule_metrics: dict[str, Any],
) -> str | None:
    """Determine which baseline performs better based on F1 + top-k average.

    Returns 'ml', 'rule_based', 'tie', or None if comparison not possible.
    """
    ml_f1 = ml_metrics.get("f1")
    rule_f1 = rule_metrics.get("f1")
    if ml_f1 is None or rule_f1 is None:
        return None

    # Use F1 as primary, average precision@k as tiebreaker
    if ml_f1 > rule_f1:
        return "ml"
    if rule_f1 > ml_f1:
        return "rule_based"

    # Tie on F1: compare avg precision@k
    ml_topk = ml_metrics.get("top_k", {})
    rule_topk = rule_metrics.get("top_k", {})
    ml_avg = (
        sum(v for v in ml_topk.values()) / len(ml_topk) if ml_topk else 0
    )
    rule_avg = (
        sum(v for v in rule_topk.values()) / len(rule_topk) if rule_topk else 0
    )

    if ml_avg > rule_avg:
        return "ml"
    if rule_avg > ml_avg:
        return "rule_based"
    return "tie"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare ML baseline vs rule-based baseline"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to training dataset parquet file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(BACKEND_ROOT / "models"),
        help="Directory for artifacts (default: models/)",
    )
    parser.add_argument(
        "--train-snapshots",
        type=int,
        default=14,
        help="Number of earliest snapshot dates for training (default: 14)",
    )
    args = parser.parse_args(argv)

    # Determine dataset path
    if args.dataset:
        dataset_path = Path(args.dataset)
    else:
        data_dir = BACKEND_ROOT / "data"
        parquet_files = sorted(data_dir.glob("training_dataset_*.parquet"))
        if parquet_files:
            dataset_path = parquet_files[-1]
        else:
            dataset_path = data_dir / "full_training_dataset.parquet"

    if not dataset_path.exists():
        print(f"ERROR: Dataset not found at {dataset_path}")
        return 1

    print(f"Loading dataset: {dataset_path}")
    df = pd.read_parquet(str(dataset_path))
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Label distribution: pos={df['label'].sum()}, neg={len(df) - df['label'].sum()}")

    run_comparison(
        df,
        output_dir=args.output_dir,
        train_snapshots=args.train_snapshots,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
