"""
Unit tests for train_baseline.py (Phase 3 training pipeline).

Uses synthetic DataFrames (no DB needed) to test:
  - Feature column identification
  - Time-based train/validation split
  - Evaluation metrics computation
  - Model training with both balanced and single-class data
  - Artifact saving and loading
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from scripts.train_baseline import (
    CATEGORICAL_COLUMNS,
    EVAL_K_VALUES,
    META_COLUMNS,
    _build_preprocessor,
    _compute_metrics,
    _identify_feature_columns,
    _save_artifact,
    _time_based_split,
    _train_model,
    train_pipeline,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A minimal synthetic dataset with all required column types."""
    np.random.seed(42)
    n = 100

    data: dict[str, list] = {
        # Metadata (should be dropped)
        "snapshot_date": [f"2026-07-{d:02d}" for d in np.random.randint(10, 29, n)],
        "target_date": [f"2026-07-{d+1:02d}" for d in np.random.randint(10, 28, n)],
        "user_id": ["user-001"] * n,
        "task_id": [f"task-{i:03d}" for i in range(n)],
        "task_title_hint": [f"Task {i}" for i in range(n)],
        "user_timezone": ["Asia/Saigon"] * n,
        "target_weekday_name": np.random.choice(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], n
        ),
        # Categorical
        "status_at_d": np.random.choice(
            ["todo", "completed", "skipped", "deferred"], n, p=[0.7, 0.2, 0.05, 0.05]
        ),
        # Numeric
        "task_age_days": np.random.randint(0, 30, n).tolist(),
        "deadline_relative_days": np.random.randint(-10, 20, n).tolist(),
        "description_length": np.random.randint(0, 200, n).tolist(),
        "user_total_open_tasks": np.random.randint(50, 500, n).tolist(),
        "user_scheduled_count": np.random.randint(30, 300, n).tolist(),
        "user_flexible_count": np.random.randint(0, 50, n).tolist(),
        "user_planned_count_7d": np.random.randint(0, 100, n).tolist(),
        "days_since_last_plan": np.random.randint(0, 30, n).tolist(),
        "days_since_last_completion": np.random.choice(
            [1, 2, 3, 5, 10, 9999], n
        ).tolist(),
        # Binary
        "has_deadline": np.random.choice([True, False], n).tolist(),
        "is_overdue": np.random.choice([True, False], n).tolist(),
        "has_estimated_duration": np.random.choice([True, False], n).tolist(),
        "priority_urgent": np.random.choice([True, False], n).tolist(),
        "priority_high": np.random.choice([True, False], n).tolist(),
        "priority_normal": np.random.choice([True, False], n).tolist(),
        "priority_low": np.random.choice([True, False], n).tolist(),
        "task_type_scheduled": np.random.choice([True, False], n).tolist(),
        "task_type_flexible": np.random.choice([True, False], n).tolist(),
        "num_tags": np.random.randint(0, 5, n).tolist(),
        "has_description": np.random.choice([True, False], n).tolist(),
        "status_is_planned": np.random.choice([True, False], n).tolist(),
        "status_is_deferred": np.random.choice([True, False], n).tolist(),
        "status_is_skipped": np.random.choice([True, False], n).tolist(),
        "has_plan_for_past_or_today": np.random.choice([True, False], n).tolist(),
        "completion_count_7d": np.random.randint(0, 10, n).tolist(),
        "deferral_count_7d": np.random.randint(0, 5, n).tolist(),
        "move_count_7d": np.random.randint(0, 3, n).tolist(),
        "skip_count_7d": np.random.randint(0, 3, n).tolist(),
        "update_count_7d": np.random.randint(0, 5, n).tolist(),
        "user_completed_count_7d": np.random.randint(0, 20, n).tolist(),
        "user_completion_rate_7d": np.random.uniform(0, 1, n).round(4).tolist(),
        "target_day_of_week": np.random.randint(0, 7, n).tolist(),
        "target_is_monday": np.random.choice([True, False], n).tolist(),
        "target_is_friday": np.random.choice([True, False], n).tolist(),
        "target_is_weekend": np.random.choice([True, False], n).tolist(),
        "target_is_day_off": np.random.choice([True, False], n).tolist(),
        # Target
        "label": np.random.choice([0, 1], n, p=[0.85, 0.15]).tolist(),
    }
    df = pd.DataFrame(data)

    # Ensure at least some positive labels
    if df["label"].sum() == 0:
        df.loc[0, "label"] = 1
    return df


@pytest.fixture
def single_class_df(sample_df: pd.DataFrame) -> pd.DataFrame:
    """Same columns but all labels = 0 (no positive class)."""
    df = sample_df.copy()
    df["label"] = 0
    return df


# ===========================================================================
# 1. Feature identification
# ===========================================================================


class TestIdentifyFeatureColumns:
    def test_identifies_all_groups(self, sample_df: pd.DataFrame):
        groups = _identify_feature_columns(sample_df)
        assert "numeric" in groups
        assert "categorical" in groups
        assert "binary" in groups
        assert len(groups["numeric"]) > 0
        assert len(groups["categorical"]) > 0
        assert len(groups["binary"]) > 0
        assert "status_at_d" in groups["categorical"]
        assert "task_age_days" in groups["numeric"]
        assert "has_deadline" in groups["binary"]
        assert "label" not in sum(groups.values(), [])
        assert "snapshot_date" not in sum(groups.values(), [])

    def test_all_numeric_or_binary_except_categorical(
        self, sample_df: pd.DataFrame
    ):
        groups = _identify_feature_columns(sample_df)
        all_features = (
            groups["numeric"] + groups["categorical"] + groups["binary"]
        )
        all_except_label_meta = (
            set(sample_df.columns)
            - {*META_COLUMNS, "label"}
        )
        # Every non-meta, non-label column should be in exactly one group
        assert set(all_features) == all_except_label_meta


# ===========================================================================
# 2. Time-based split
# ===========================================================================


class TestTimeBasedSplit:
    def test_splits_by_date(self, sample_df: pd.DataFrame):
        train_df, val_df = _time_based_split(sample_df, train_snapshots=14)
        # Get snapshot dates
        train_dates = set(train_df["snapshot_date"].unique())
        val_dates = set(val_df["snapshot_date"].unique())
        # No overlap
        assert train_dates.isdisjoint(val_dates)
        # All train dates < all val dates (sort strings which is fine for YYYY-MM-DD)
        train_sorted = sorted(train_dates)
        val_sorted = sorted(val_dates)
        assert train_sorted[-1] < val_sorted[0]

    def test_handles_single_date(self):
        df = pd.DataFrame({
            "snapshot_date": ["2026-07-15"] * 10,
            "some_feat": range(10),
            "label": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        })
        train_df, val_df = _time_based_split(df, train_snapshots=14)
        # Fallback to 80/20 row split
        assert len(train_df) >= len(val_df)

    def test_adjusts_when_val_dates_empty(self, sample_df: pd.DataFrame):
        # With more train_snapshots than available dates
        train_df, val_df = _time_based_split(sample_df, train_snapshots=99)
        assert len(train_df) > 0
        assert len(val_df) > 0
        train_dates = set(train_df["snapshot_date"].unique())
        val_dates = set(val_df["snapshot_date"].unique())
        assert train_dates.isdisjoint(val_dates)


# ===========================================================================
# 3. Evaluation metrics
# ===========================================================================


class TestComputeMetrics:
    def test_perfect_prediction(self):
        y_true = np.array([1, 0, 1, 0, 1])
        y_score = np.array([0.99, 0.01, 0.98, 0.02, 0.97])
        metrics = _compute_metrics(y_true, y_score, k_values=[1, 3, 5])
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["roc_auc"] >= 0.9

    def test_all_negative(self):
        y_true = np.zeros(10)
        y_score = np.zeros(10)
        metrics = _compute_metrics(y_true, y_score)
        assert metrics["n_positive"] == 0
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["roc_auc"] is None

    def test_top_k_metrics(self):
        """precision@k should reflect ranking quality."""
        y_true = np.array([1, 0, 0, 1, 0])
        y_score = np.array([0.9, 0.7, 0.5, 0.3, 0.1])
        metrics = _compute_metrics(y_true, y_score, k_values=[1, 2, 3])
        # Top 1: score=0.9, true=1 → precision@1=1.0, recall@1=0.5 (1/2 positives)
        assert metrics["top_k"]["precision@1"] == 1.0
        assert metrics["top_k"]["recall@1"] == 0.5
        # Top 2: scores=[0.9, 0.7], true=[1, 0] → precision@2=0.5
        assert metrics["top_k"]["precision@2"] == 0.5

    def test_handles_single_class_score(self):
        y_true = np.zeros(5)
        y_score = np.zeros(5)
        metrics = _compute_metrics(y_true, y_score)
        assert metrics["roc_auc"] is None
        assert metrics["average_precision"] is None
        # This should not crash


# ===========================================================================
# 4. Preprocessor building
# ===========================================================================


class TestBuildPreprocessor:
    def test_returns_column_transformer(self, sample_df: pd.DataFrame):
        groups = _identify_feature_columns(sample_df)
        preprocessor = _build_preprocessor(groups)
        assert hasattr(preprocessor, "fit_transform")
        assert hasattr(preprocessor, "get_feature_names_out")

    def test_transform_produces_correct_shape(self, sample_df: pd.DataFrame):
        groups = _identify_feature_columns(sample_df)
        preprocessor = _build_preprocessor(groups)
        # Figure out feature columns
        feature_cols = groups["numeric"] + groups["categorical"] + groups["binary"]
        X = sample_df[feature_cols]
        transformed = preprocessor.fit_transform(X)
        # Should produce a 2D array with n rows = len(sample_df)
        assert transformed.shape[0] == len(sample_df)
        assert transformed.shape[1] > 0


# ===========================================================================
# 5. Model training
# ===========================================================================


class TestTrainModel:
    def test_trains_on_two_classes(self):
        X = np.random.randn(50, 5)
        y = np.array([0] * 30 + [1] * 20)
        model = _train_model(X, y)
        assert hasattr(model, "predict")
        preds = model.predict(X)
        assert len(preds) == 50

    def test_falls_back_to_dummy_on_single_class(self):
        X = np.random.randn(50, 5)
        y = np.zeros(50)
        with pytest.warns(UserWarning, match="Only one class"):
            model = _train_model(X, y)
        from sklearn.dummy import DummyClassifier
        assert isinstance(model, DummyClassifier)

    def test_accepts_manual_scale_pos_weight(self):
        X = np.random.randn(50, 5)
        y = np.array([0] * 40 + [1] * 10)
        model = _train_model(X, y, scale_pos_weight=10.0)
        preds = model.predict(X)
        assert len(preds) == 50


# ===========================================================================
# 6. Artifact saving
# ===========================================================================


class TestSaveArtifact:
    def test_saves_all_files(self, sample_df: pd.DataFrame):
        import joblib
        from sklearn.pipeline import Pipeline
        from sklearn.linear_model import LogisticRegression

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            groups = _identify_feature_columns(sample_df)
            # Use the actual preprocessor (handles cat encoding + numeric scaling)
            preprocessor = _build_preprocessor(groups)
            pipeline = Pipeline([
                ("preprocessor", preprocessor),
                ("clf", LogisticRegression(max_iter=100)),
            ])
            feature_cols = (
                groups["numeric"] + groups["categorical"] + groups["binary"]
            )
            pipeline.fit(sample_df[feature_cols], sample_df["label"])
            metrics = {"test": 1.0, "n_total": 100}

            _save_artifact(pipeline, metrics, groups, output_dir)

            assert (output_dir / "model_pipeline.joblib").exists()
            assert (output_dir / "evaluation_report.json").exists()
            assert (output_dir / "feature_groups.json").exists()
            assert (output_dir / "metadata.json").exists()

            # Verify model can be loaded and used
            loaded = joblib.load(str(output_dir / "model_pipeline.joblib"))
            assert hasattr(loaded, "predict")

            # Verify JSON report is valid
            with open(output_dir / "evaluation_report.json") as f:
                report = json.load(f)
            assert report["test"] == 1.0
            assert report["n_total"] == 100

    def test_creates_directory_if_not_exists(self, sample_df: pd.DataFrame):
        import joblib
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        from sklearn.dummy import DummyClassifier

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "models"
            groups = _identify_feature_columns(sample_df)
            pipeline = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", DummyClassifier(strategy="prior")),
            ])
            pipeline.fit(sample_df[["task_age_days"]], sample_df["label"])
            metrics = {}

            # Should not raise (creates dirs)
            _save_artifact(pipeline, metrics, groups, output_dir)
            assert output_dir.exists()
            assert (output_dir / "model_pipeline.joblib").exists()


# ===========================================================================
# 7. End-to-end pipeline
# ===========================================================================


class TestTrainPipeline:
    def test_end_to_end(self, sample_df: pd.DataFrame):
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics = train_pipeline(
                sample_df,
                output_dir=tmpdir,
                train_snapshots=14,
            )
            assert metrics["n_total"] > 0
            assert metrics["n_positive"] > 0  # sample data has positive labels
            assert metrics["model_type"] == "LogisticRegression"
            assert "top_k" in metrics

    def test_handles_single_class(self, single_class_df: pd.DataFrame):
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics = train_pipeline(
                single_class_df,
                output_dir=tmpdir,
                train_snapshots=14,
            )
            # Should complete without error, using DummyClassifier
            assert metrics["model_type"] == "DummyClassifier"
            assert metrics["n_positive"] == 0
            assert "warning" in metrics

    def test_produces_loadable_artifact(self, sample_df: pd.DataFrame):
        import joblib

        with tempfile.TemporaryDirectory() as tmpdir:
            train_pipeline(sample_df, output_dir=tmpdir, train_snapshots=14)

            # Load and use the model
            pipeline = joblib.load(str(Path(tmpdir) / "model_pipeline.joblib"))
            # Prepare input matching training columns
            groups = _identify_feature_columns(sample_df)
            feature_cols = groups["numeric"] + groups["categorical"] + groups["binary"]
            X_sample = sample_df[feature_cols].iloc[:5]
            preds = pipeline.predict(X_sample)
            probas = pipeline.predict_proba(X_sample)
            assert len(preds) == 5
            assert probas.shape == (5, 2)
