"""
Analyze the ML training dataset for label distribution, class imbalance,
feature correlation, and actionable insights for model training.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main(path: str) -> int:
    df = pd.read_parquet(path)

    print("=" * 70)
    print("1. OVERALL LABEL DISTRIBUTION")
    print("=" * 70)
    vc = df["label"].value_counts()
    print(f"  Positive (1): {vc.get(1, 0):>6} ({vc.get(1, 0)/len(df)*100:.2f}%)")
    print(f"  Negative (0): {vc.get(0, 0):>6} ({vc.get(0, 0)/len(df)*100:.2f}%)")
    neg_pos_ratio = vc.get(0, 0) / max(vc.get(1, 0), 1)
    print(f"  Imbalance ratio (neg:pos): {neg_pos_ratio:.1f}:1")
    print()

    # --- By snapshot date ---
    print("=" * 70)
    print("2. LABELS BY SNAPSHOT DATE")
    print("=" * 70)
    by_date = df.groupby("snapshot_date")["label"].agg(["count", "sum", "mean"])
    by_date.columns = ["total", "positive", "positive_rate"]
    by_date["positive_rate"] = (by_date["positive_rate"] * 100).round(2)
    print(by_date.to_string())
    print()

    # --- By target day of week ---
    print("=" * 70)
    print("3. LABELS BY TARGET DAY OF WEEK")
    print("=" * 70)
    dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    df["dow_name"] = df["target_day_of_week"].map(dow_map)
    by_dow = df.groupby("dow_name")["label"].agg(["count", "sum", "mean"])
    by_dow.columns = ["total", "positive", "positive_rate"]
    by_dow["positive_rate"] = (by_dow["positive_rate"] * 100).round(2)
    print(by_dow.reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]).to_string())
    print()

    # --- By day off ---
    print("=" * 70)
    print("4. LABELS BY DAY OFF vs WORK DAY")
    print("=" * 70)
    by_off = df.groupby("target_is_day_off")["label"].agg(["count", "sum", "mean"])
    by_off.columns = ["total", "positive", "positive_rate"]
    by_off["positive_rate"] = (by_off["positive_rate"] * 100).round(2)
    by_off.index = by_off.index.map({True: "Day off", False: "Work day"})
    print(by_off.to_string())
    print()

    # --- By task type ---
    print("=" * 70)
    print("5. LABELS BY TASK TYPE")
    print("=" * 70)
    by_type = df.groupby(["task_type_scheduled", "task_type_flexible"])["label"].agg(
        ["count", "sum", "mean"]
    )
    by_type.columns = ["total", "positive", "positive_rate"]
    by_type["positive_rate"] = (by_type["positive_rate"] * 100).round(2)
    by_type.index = by_type.index.map(
        lambda x: "scheduled" if x[0] else ("flexible" if x[1] else "unknown")
    )
    print(by_type.to_string())
    print()

    # --- FEATURE COMPARISON: POSITIVE vs NEGATIVE ---
    print("=" * 70)
    print("6. FEATURE MEANS: POSITIVE vs NEGATIVE")
    print("=" * 70)
    pos = df[df["label"] == 1]
    neg = df[df["label"] == 0]

    features = [
        "task_age_days",
        "has_deadline",
        "is_overdue",
        "deadline_relative_days",
        "estimated_duration",
        "has_estimated_duration",
        "priority_urgent",
        "priority_high",
        "priority_normal",
        "priority_low",
        "task_type_scheduled",
        "task_type_flexible",
        "num_tags",
        "has_description",
        "has_plan_for_past_or_today",
        "completion_count_7d",
        "deferral_count_7d",
        "move_count_7d",
        "days_since_last_completion",
        "user_total_open_tasks",
        "user_completion_rate_7d",
        "target_day_of_week",
        "target_is_weekend",
        "target_is_day_off",
    ]

    print(f"  {'Feature':40s} {'Pos':>8s} {'Neg':>8s} {'Diff':>8s}")
    print("  " + "-" * 66)
    for feat in features:
        if feat in df.columns:
            pm = pos[feat].mean()
            nm = neg[feat].mean()
            diff = pm - nm
            print(f"  {feat:40s} {pm:8.4f} {nm:8.4f} {diff:+8.4f}")
    print()

    # --- Status at D ---
    print("=" * 70)
    print("7. STATUS AT D: POSITIVE vs NEGATIVE")
    print("=" * 70)
    print("Positive tasks status:")
    print(pos["status_at_d"].value_counts().to_string())
    print()
    print("Negative tasks status:")
    print(neg["status_at_d"].value_counts().to_string())
    print()

    # --- Status flags ---
    print("=" * 70)
    print("8. STATUS FLAGS: POSITIVE vs NEGATIVE")
    print("=" * 70)
    for flag in ["status_is_planned", "status_is_deferred", "status_is_skipped"]:
        if flag in df.columns:
            pct_pos = pos[flag].mean() * 100
            pct_neg = neg[flag].mean() * 100
            print(f"  {flag:30s}: pos={pct_pos:.1f}%  neg={pct_neg:.1f}%")
    print()

    # --- CORRELATION ANALYSIS ---
    print("=" * 70)
    print("9. PEARSON CORRELATION WITH LABEL")
    print("=" * 70)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != "label"]

    # Only use columns with sufficient variance
    valid_cols = [c for c in numeric_cols if df[c].nunique() > 1]
    corrs = df[valid_cols + ["label"]].corr()["label"].drop("label").sort_values(ascending=False)

    print(f"  {'Feature':40s} {'Correlation':>12s}")
    print("  " + "-" * 54)
    for feat, corr_val in corrs.items():
        print(f"  {feat:40s} {corr_val:+.6f}")
    print()

    # --- TOP/BOTTOM FEATURES ---
    print("=" * 70)
    print("10. TOP 10 FEATURES BY ABSOLUTE CORRELATION")
    print("=" * 70)
    top = corrs.abs().sort_values(ascending=False).head(10)
    for feat in top.index:
        print(f"  {feat:40s} r={corrs[feat]:+.6f}")
    print()

    # --- CLASS IMBALANCE HANDLING RECOMMENDATIONS ---
    print("=" * 70)
    print("11. CLASS IMBALANCE ANALYSIS")
    print("=" * 70)
    print(f"  Positive examples: {len(pos)} ({len(pos)/len(df)*100:.2f}%)")
    print(f"  Negative examples: {len(neg)} ({len(neg)/len(df)*100:.2f}%)")
    print(f"  Imbalance ratio: {neg_pos_ratio:.1f}:1")
    print()

    # Stratified split possible?
    if len(pos) >= 10:
        print("  Status: SUFFICIENT positive examples for train/val/test split")
        n_train = int(len(pos) * 0.7)
        n_val = int(len(pos) * 0.15)
        n_test = len(pos) - n_train - n_val
        print(f"  Recommended: {n_train} train / {n_val} val / {n_test} test (positive)")
    else:
        print("  Status: INSUFFICIENT positive examples - consider upsampling or SMOTE")

    print()
    print(f"  Recommended techniques:")
    print(f"    - Class weighting (scale_pos_weight = {neg_pos_ratio:.1f})")
    print(f"    - Undersample majority / oversample minority")
    print(f"    - Use precision@k and recall@k instead of accuracy")

    return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/test_training_dataset_v2.parquet"
    raise SystemExit(main(path))
