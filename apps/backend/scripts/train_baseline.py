"""
Phase 3: Baseline Training — Next-Day Task Prediction
=======================================================

Trains a weighted LogisticRegression baseline on the dataset produced
by build_ml_dataset.py (Phase 2).

Steps:
  1. Load parquet dataset
  2. Time-based train/validation split (avoids future leakage)
  3. Feature preprocessing: scale numerics, encode categoricals
  4. Train weighted LogisticRegression (class_weight='balanced')
  5. Evaluate: precision@k, recall@k, F1, AUROC
  6. Save model artifact (joblib) + evaluation report (JSON)

Usage:
    python scripts/train_baseline.py \\
        --dataset data/full_training_dataset.parquet \\
        --output-dir models/ \\
        --train-snapshots 14          # first N snapshots for train, rest for val

If no positive labels are present in the dataset, the pipeline still runs:
a DummyClassifier is fitted as a placeholder, and the full evaluation
infrastructure is saved for when real user data becomes available.
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
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
# Constants
# ---------------------------------------------------------------------------

# Columns that are metadata / not features
META_COLUMNS: list[str] = [
    "snapshot_date",
    "target_date",
    "user_id",
    "task_id",
    "task_title_hint",
    "user_timezone",
    "target_weekday_name",
]

# Categorical columns (need encoding)
CATEGORICAL_COLUMNS: list[str] = [
    "status_at_d",
]

# Target column
TARGET_COLUMN = "label"

# Default list of evaluation k values (precision@k, recall@k)
EVAL_K_VALUES = [1, 3, 5, 10, 20]

# ---------------------------------------------------------------------------
# Feature pipeline helpers
# ---------------------------------------------------------------------------


def _identify_feature_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Identify feature column groups from the DataFrame.

    Returns:
        { 'numeric': [...], 'categorical': [...], 'binary': [...] }
    """
    all_cols = set(df.columns) - {TARGET_COLUMN} - set(META_COLUMNS)

    numeric: list[str] = []
    categorical: list[str] = []
    binary: list[str] = []

    for col in sorted(all_cols):
        if col in CATEGORICAL_COLUMNS:
            categorical.append(col)
            continue

        dtype = df[col].dtype
        if pd.api.types.is_bool_dtype(dtype):
            binary.append(col)
        elif pd.api.types.is_integer_dtype(dtype) or pd.api.types.is_float_dtype(dtype):
            nunique = df[col].nunique()
            if nunique <= 2:
                binary.append(col)
            else:
                numeric.append(col)
        else:
            # Treat anything else as categorical
            categorical.append(col)

    return {
        "numeric": numeric,
        "categorical": categorical,
        "binary": binary,
    }


def _build_preprocessor(col_groups: dict[str, list[str]]) -> Any:
    """Build a sklearn ColumnTransformer for feature preprocessing.

    - Numeric: StandardScaler (mean=0, std=1) — robust to outliers via clipping later
    - Categorical: OneHotEncoder (handle unknown categories seen at inference)
    - Binary: passthrough (already 0/1)
    """
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    transformers: list[tuple[str, Any, list[str]]] = []

    if col_groups["numeric"]:
        transformers.append(
            ("num", StandardScaler(), col_groups["numeric"])
        )
    if col_groups["categorical"]:
        transformers.append(
            ("cat", OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
                min_frequency=1,
            ), col_groups["categorical"])
        )
    if col_groups["binary"]:
        transformers.append(
            ("bin", "passthrough", col_groups["binary"])
        )

    if not transformers:
        raise ValueError("No feature columns found! Check dataset.")

    return ColumnTransformer(transformers, remainder="drop")


# ---------------------------------------------------------------------------
# Train / validation split (time-based)
# ---------------------------------------------------------------------------


def _time_based_split(
    df: pd.DataFrame,
    train_snapshots: int = 14,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset by snapshot date (time-ordered, no future leakage).

    Args:
        df: Full dataset with 'snapshot_date' column (YYYY-MM-DD strings)
        train_snapshots: Number of earliest snapshot dates to use for training

    Returns:
        (train_df, val_df)
    """
    snapshot_dates = sorted(df["snapshot_date"].unique())
    if len(snapshot_dates) < 2:
        # Fallback: 80/20 row-level split (not ideal but only option)
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx].copy()
        val_df = df.iloc[split_idx:].copy()
        return train_df, val_df

    train_dates = set(snapshot_dates[:train_snapshots])
    val_dates = set(snapshot_dates[train_snapshots:])

    # If val_dates is empty, reduce train_snapshots
    if not val_dates and len(snapshot_dates) > 1:
        split = max(1, len(snapshot_dates) * 4 // 5)
        train_dates = set(snapshot_dates[:split])
        val_dates = set(snapshot_dates[split:])

    train_df = df[df["snapshot_date"].isin(train_dates)].copy()
    val_df = df[df["snapshot_date"].isin(val_dates)].copy()
    return train_df, val_df


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------


def _compute_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    k_values: list[int] | None = None,
) -> dict[str, Any]:
    """Compute evaluation metrics for binary classification with ranking.

    Returns dict with:
        - precision_at_k, recall_at_k for each k in k_values
        - average_precision, f1_score, roc_auc, log_loss
        - label distribution summary
    """
    from sklearn.metrics import (
        average_precision_score,
        f1_score,
        log_loss,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    if k_values is None:
        k_values = EVAL_K_VALUES

    y_pred = (y_score >= 0.5).astype(int)
    n_pos = int(y_true.sum())

    metrics: dict[str, Any] = {
        "n_total": int(len(y_true)),
        "n_positive": n_pos,
        "n_negative": int(len(y_true) - n_pos),
        "positive_ratio": round(n_pos / max(len(y_true), 1), 4),
    }

    # Standard classification metrics (useful when both classes present)
    if n_pos > 0 and n_pos < len(y_true):
        try:
            metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
        except (ValueError, Exception):
            metrics["roc_auc"] = None
        try:
            metrics["average_precision"] = round(
                float(average_precision_score(y_true, y_score)), 4
            )
        except (ValueError, Exception):
            metrics["average_precision"] = None
        try:
            metrics["log_loss"] = round(float(log_loss(y_true, y_score)), 4)
        except (ValueError, Exception):
            metrics["log_loss"] = None
    else:
        metrics["roc_auc"] = None
        metrics["average_precision"] = None
        metrics["log_loss"] = None

    # Precision / Recall at thresholds
    metrics["precision"] = round(float(precision_score(y_true, y_pred, zero_division=0)), 4)
    metrics["recall"] = round(float(recall_score(y_true, y_pred, zero_division=0)), 4)
    metrics["f1"] = round(float(f1_score(y_true, y_pred, zero_division=0)), 4)

    # Precision@k and Recall@k (for ranking / top-k recommendation)
    top_k_metrics: dict[str, Any] = {}
    for k in k_values:
        if k > len(y_true):
            break
        # Top-k predictions by score
        top_k_idx = np.argsort(y_score)[-k:][::-1]
        top_k_true = y_true[top_k_idx]
        n_relevant = int(top_k_true.sum())

        precision_at_k = n_relevant / k
        recall_at_k = n_relevant / max(n_pos, 1)

        top_k_metrics[f"precision@{k}"] = round(precision_at_k, 4)
        top_k_metrics[f"recall@{k}"] = round(recall_at_k, 4)

    metrics["top_k"] = top_k_metrics
    return metrics


# ---------------------------------------------------------------------------
# Model loading/saving
# ---------------------------------------------------------------------------


def _save_artifact(
    pipeline: Any,
    metrics: dict[str, Any],
    col_groups: dict[str, list[str]],
    output_dir: Path,
) -> None:
    """Save model pipeline + metadata to disk."""
    import joblib

    output_dir.mkdir(parents=True, exist_ok=True)

    # Model artifact
    model_path = output_dir / "model_pipeline.joblib"
    joblib.dump(pipeline, model_path)
    print(f"  Model saved: {model_path} ({model_path.stat().st_size / 1024:.1f} KB)")

    # Evaluation report
    report_path = output_dir / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  Report saved: {report_path}")

    # Feature list (for inference reference)
    feat_path = output_dir / "feature_groups.json"
    with open(feat_path, "w") as f:
        json.dump(col_groups, f, indent=2)
    print(f"  Features saved: {feat_path}")

    # Training metadata
    meta = {
        "model_type": type(pipeline[-1]).__name__,
        "feature_pipeline": type(pipeline[0]).__name__,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_features_raw": sum(len(v) for v in col_groups.values()),
        "feature_groups": {k: len(v) for k, v in col_groups.items()},
    }
    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Metadata saved: {meta_path}")


# ---------------------------------------------------------------------------
# Main training pipeline
# ---------------------------------------------------------------------------


def _train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    scale_pos_weight: float | None = None,
) -> Any:
    """Train the baseline model.

    Uses LogisticRegression with:
        - class_weight='balanced' (auto weight by inverse frequency)
          OR manual scale_pos_weight for the positive class
        - solver='lbfgs' (default in sklearn 1.6+, numerically stable)
        - max_iter=1000 for convergence
        - random_state=42 for reproducibility

    LogisticRegression is trained with log-loss, so its raw probabilities
    are already well-calibrated. No extra CalibratedClassifierCV is needed
    for the baseline. If real-world calibration drift is observed later,
    IsotonicRegression or Platt scaling can be added in Phase 4.

    If only one class is present, fits a DummyClassifier as placeholder.
    The placeholder returns probability 1.0 for the majority class and
    0.0 for the missing class, which is correct for evaluation.
    """
    from sklearn.linear_model import LogisticRegression

    unique = np.unique(y_train)
    if len(unique) < 2:
        warnings.warn(
            f"Only one class ({unique[0]}) present in training data. "
            "Fitting DummyClassifier as placeholder."
        )
        from sklearn.dummy import DummyClassifier
        model = DummyClassifier(strategy="prior", random_state=42)
        model.fit(X_train, y_train)
        return model

    if scale_pos_weight is not None:
        model = LogisticRegression(
            class_weight={0: 1.0, 1: scale_pos_weight},
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )
    else:
        model = LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )

    model.fit(X_train, y_train)
    return model


def train_pipeline(
    df: pd.DataFrame,
    *,
    output_dir: str | Path = "models/",
    train_snapshots: int = 14,
    scale_pos_weight: float | None = None,
) -> dict[str, Any]:
    """Run the full training pipeline.

    Args:
        df: Full training dataset (parquet loaded as DataFrame)
        output_dir: Directory to save artifacts
        train_snapshots: Number of earliest snapshots for training
        scale_pos_weight: If None, uses class_weight='balanced'.
                          If set, uses manual weight for positive class.

    Returns:
        metrics dict with evaluation results
    """
    from sklearn.pipeline import Pipeline

    # --- 1. Identify features ---
    col_groups = _identify_feature_columns(df)
    print(f"Feature groups:")
    for group, cols in col_groups.items():
        print(f"  {group}: {len(cols)} features")
        for c in cols:
            print(f"    - {c}")

    # --- 2. Build preprocessor ---
    preprocessor = _build_preprocessor(col_groups)

    # --- 3. Time-based split ---
    train_df, val_df = _time_based_split(df, train_snapshots=train_snapshots)
    print(f"\nSplit: {len(train_df)} train / {len(val_df)} validation rows")
    print(
        f"  Train dates: {sorted(train_df['snapshot_date'].unique())}"
    )
    print(
        f"  Val dates:   {sorted(val_df['snapshot_date'].unique())}"
    )
    train_pos = train_df[TARGET_COLUMN].sum()
    val_pos = val_df[TARGET_COLUMN].sum()
    print(
        f"  Train labels: {train_pos} positive, "
        f"{len(train_df) - train_pos} negative"
    )
    print(
        f"  Val labels:   {val_pos} positive, "
        f"{len(val_df) - val_pos} negative"
    )

    # --- 4. Prepare feature matrix X and target y ---
    feature_cols = (
        col_groups["numeric"]
        + col_groups["categorical"]
        + col_groups["binary"]
    )
    # Safety: only keep columns that actually exist in the DataFrame
    available = set(train_df.columns)
    feature_cols = [c for c in feature_cols if c in available]
    print(f"  Features used: {len(feature_cols)}")
    X_train = train_df[feature_cols].copy()
    y_train = train_df[TARGET_COLUMN].values
    X_val = val_df[feature_cols].copy()
    y_val = val_df[TARGET_COLUMN].values

    # --- 5. Build and fit pipeline (single fit, no double-transform) ---
    # Fit preprocessor first, then build the pipeline with the trained model
    X_train_transformed = preprocessor.fit_transform(X_train)
    model = _train_model(
        X_train_transformed,
        y_train,
        scale_pos_weight=scale_pos_weight,
    )
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", model),
    ])

    # --- 6. Predict (safe for DummyClassifier with single-class output) ---
    proba = pipeline.predict_proba(X_val)
    if proba.shape[1] >= 2:
        y_score = proba[:, 1]
    else:
        # Only one class in training data → DummyClassifier returns 1 column
        # If the only class is 0, positive probability = 0
        y_score = np.zeros(len(proba))
    y_pred = pipeline.predict(X_val)

    # --- 7. Evaluate ---
    metrics = _compute_metrics(y_val, y_score)
    metrics["train_label_distribution"] = {
        "positive": int(train_pos),
        "negative": int(len(train_df) - train_pos),
    }
    metrics["val_label_distribution"] = {
        "positive": int(val_pos),
        "negative": int(len(val_df) - val_pos),
    }
    metrics["model_type"] = type(pipeline[-1]).__name__

    # If DummyClassifier was used, note that
    if "DummyClassifier" in metrics["model_type"]:
        metrics["warning"] = (
            "Only one class in training data. "
            "DummyClassifier fitted as placeholder."
        )

    print(f"\n=== Evaluation ===")
    print(f"Model: {metrics['model_type']}")
    print(f"Val set: {metrics['n_total']} rows ({metrics['n_positive']} positive)")
    print(f"  Precision: {metrics['precision']}")
    print(f"  Recall:    {metrics['recall']}")
    print(f"  F1:        {metrics['f1']}")
    if metrics["roc_auc"] is not None:
        print(f"  AUROC:     {metrics['roc_auc']}")
    if metrics["average_precision"] is not None:
        print(f"  Avg Prec:  {metrics['average_precision']}")
    print(f"\n  Top-k metrics:")
    for k, v in sorted(metrics["top_k"].items()):
        print(f"    {k}: {v}")

    # --- 8. Save artifact ---
    print(f"\n=== Saving artifacts ===")
    output_path = Path(output_dir) if not isinstance(output_dir, Path) else output_dir
    _save_artifact(pipeline, metrics, col_groups, output_path)

    return metrics


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 3: Train baseline model for next-day task prediction"
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
        help="Directory for model artifacts (default: models/)",
    )
    parser.add_argument(
        "--train-snapshots",
        type=int,
        default=14,
        help="Number of earliest snapshot dates to use for training (default: 14)",
    )
    parser.add_argument(
        "--scale-pos-weight",
        type=float,
        default=None,
        help="Manual positive class weight (default: auto-balanced)",
    )
    args = parser.parse_args(argv)

    # Determine dataset path
    if args.dataset:
        dataset_path = Path(args.dataset)
    else:
        # Auto-detect latest dataset
        data_dir = BACKEND_ROOT / "data"
        parquet_files = sorted(data_dir.glob("training_dataset_*.parquet"))
        if parquet_files:
            dataset_path = parquet_files[-1]
            print(f"Auto-detected dataset: {dataset_path}")
        else:
            # Fall back to full_training_dataset.parquet
            dataset_path = data_dir / "full_training_dataset.parquet"

    if not dataset_path.exists():
        print(f"ERROR: Dataset not found at {dataset_path}")
        print("Run scripts/build_ml_dataset.py first to generate the dataset.")
        return 1

    print(f"Loading dataset: {dataset_path} ({dataset_path.stat().st_size / 1024:.1f} KB)")
    df = pd.read_parquet(str(dataset_path))
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Label distribution: pos={df['label'].sum()}, neg={len(df) - df['label'].sum()}")

    t0 = time.time()
    metrics = train_pipeline(
        df,
        output_dir=args.output_dir,
        train_snapshots=args.train_snapshots,
        scale_pos_weight=args.scale_pos_weight,
    )
    elapsed = time.time() - t0
    print(f"\nTotal training time: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
