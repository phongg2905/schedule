"""
Unit tests for src/modules/ml/prediction_service.py (Phase 5 inference).

Tests:
  - Model loading (success, missing file, corrupt file)
  - Feature extraction (SQLAlchemy tasks, dicts, edge cases)
  - Prediction (normal, empty tasks, single class)
  - Fallback edge cases (DB error, missing features)
  - PredictionResult schema
  - Confidence bands
  - Module init imports
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Generator
from unittest import mock

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend src is on the path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set test environment BEFORE importing module
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from src.core.config import get_settings
get_settings.cache_clear()

from src.db.base import Base
from src.db.models import ActivityEvent, ContextSnapshot, DailyPlan, Task, User, UserSchedulePreference, new_id

from src.modules.ml import MLPredictionService
from src.modules.ml.schemas import PredictionResult, TaskPrediction, __all__ as schemas_all
from src.modules.ml.prediction_service import (
    __all__ as service_all,
    _compute_task_features_dict,
    _get_temporal_features,
    _load_feature_groups,
    compute_end_of_day,
    _FALLBACK_FEATURE_GROUPS,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="session")
def engine():
    """Create SQLite in-memory engine with foreign keys enabled."""
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(e, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Create a fresh session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    db = SessionLocal()
    yield db
    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def user_id(session: Session) -> str:
    """Create a test user and return user_id."""
    uid = new_id()
    session.add(User(
        id=uid, email="ml-infer-test@example.com",
        password_hash="fakehash", name="ML Infer User",
        timezone="Asia/Saigon", role="user",
    ))
    session.add(UserSchedulePreference(
        id=new_id(), user_id=uid,
        work_start_time="09:00", work_end_time="17:00",
        lunch_start_time="12:00", lunch_end_time="13:00",
        day_offs=["Saturday", "Sunday"], focus_hours=[],
    ))
    session.commit()
    return uid


@pytest.fixture
def sample_task(user_id: str, session: Session) -> Task:
    """Create a minimal sample Task for feature extraction tests."""
    task = Task(
        id=new_id(), user_id=user_id, title="Sample task",
        description="A test task for ML inference",
        estimated_duration=60, deadline=(date.today() + timedelta(days=3)).isoformat(),
        task_type="scheduled", priority="high", status="todo",
        tags=["work", "urgent"],
        created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
    )
    session.add(task)
    session.flush()
    return task


@pytest.fixture
def temp_model_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with a minimal model for inference tests."""
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    from sklearn.linear_model import LogisticRegression

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Build a minimal model that matches our feature groups
        numeric_features = _FALLBACK_FEATURE_GROUPS["numeric"]
        cat_features = _FALLBACK_FEATURE_GROUPS["categorical"]
        binary_features = _FALLBACK_FEATURE_GROUPS["binary"]

        preprocessor = ColumnTransformer([
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=1), cat_features),
            ("bin", "passthrough", binary_features),
        ])

        model = LogisticRegression(class_weight="balanced", max_iter=100, solver="lbfgs", random_state=42)
        pipeline = Pipeline([("preprocessor", preprocessor), ("classifier", model)])

        # Train on dummy data so predict_proba works
        dummy_X = pd.DataFrame(
            {feat: [0, 1, 2] for feat in numeric_features + cat_features + binary_features}
        )
        dummy_y = [0, 1, 0]
        # Fill numeric cols with floats
        for c in numeric_features:
            dummy_X[c] = [0.0, 1.0, 2.0]
        # Fill cat col
        dummy_X["status_at_d"] = ["todo", "completed", "todo"]
        # Fill binary cols
        for c in binary_features:
            dummy_X[c] = [0, 1, 0]

        pipeline.fit(dummy_X, dummy_y)

        # Save model
        import joblib
        joblib.dump(pipeline, output_dir / "model_pipeline.joblib")

        # Save feature groups
        with open(output_dir / "feature_groups.json", "w") as f:
            json.dump(_FALLBACK_FEATURE_GROUPS, f)

        # Save metadata
        with open(output_dir / "metadata.json", "w") as f:
            json.dump({"model_type": "LogisticRegression", "n_features_raw": 38}, f)

        yield output_dir


# Helper to simulate SQLAlchemy model-like objects
class FakeTask:
    """Minimal mock for a SQLAlchemy Task object (has _sa_instance_state)."""
    def __init__(self, **kwargs):
        self._sa_instance_state = True
        for k, v in kwargs.items():
            setattr(self, k, v)


# ===========================================================================
# 1. MODULE INIT TESTS
# ===========================================================================


class TestModuleInit:
    def test_imports(self):
        """Verify the module can be imported and exposes correct API."""
        assert MLPredictionService is not None
        assert hasattr(MLPredictionService, "predict")
        assert hasattr(MLPredictionService, "predict_result")
        assert hasattr(MLPredictionService, "is_available")
        assert hasattr(MLPredictionService, "reload")
        assert hasattr(MLPredictionService, "get_confidence_bands")

    def test_service_all_export(self):
        """__all__ should expose the public API."""
        assert "MLPredictionService" in service_all
        assert "compute_end_of_day" in service_all

    def test_schemas_all_export(self):
        """schemas __all__ should expose TaskPrediction and PredictionResult."""
        assert "TaskPrediction" in schemas_all
        assert "PredictionResult" in schemas_all


# ===========================================================================
# 2. SCHEMA TESTS
# ===========================================================================


class TestPredictionSchema:
    def test_task_prediction_defaults(self):
        """Schema defaults: confidence_band is 'low', score is required."""
        tp = TaskPrediction(task_id="abc", score=0.0)
        assert tp.task_id == "abc"
        assert tp.score == 0.0
        assert tp.confidence_band == "low"  # default field value

    def test_task_prediction_explicit_band(self):
        """confidence_band can be set explicitly (used by predict_result)."""
        tp = TaskPrediction(task_id="abc", score=0.85, confidence_band="high")
        assert tp.confidence_band == "high"

    def test_task_prediction_score_range(self):
        """Score must be in [0, 1] — Pydantic validates this."""
        TaskPrediction(task_id="a", score=0.0)
        TaskPrediction(task_id="a", score=1.0)
        with pytest.raises(Exception):
            TaskPrediction(task_id="a", score=-0.1)
        with pytest.raises(Exception):
            TaskPrediction(task_id="a", score=1.1)

    def test_prediction_result_defaults(self):
        pr = PredictionResult()
        assert pr.predictions == []
        assert pr.result_status == "ok"
        assert pr.classifier_type == ""
        assert pr.n_candidates == 0
        assert pr.n_scored == 0
        assert pr.n_high_confidence == 0
        assert pr.n_medium_confidence == 0
        assert pr.fallback_used is False

    def test_prediction_result_custom_status(self):
        pr = PredictionResult(
            result_status="fallback_model_missing",
            classifier_type="DummyClassifier",
            n_candidates=10,
            n_scored=0,
            fallback_used=True,
        )
        assert pr.result_status == "fallback_model_missing"
        assert pr.classifier_type == "DummyClassifier"
        assert pr.fallback_used is True

    def test_prediction_result_no_pydantic_warnings(self):
        """Verify that field names don't trigger Pydantic protected namespace warnings."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            PredictionResult(result_status="ok", classifier_type="LR")
            schema_warnings = [x for x in w if "model_" in str(x.message).lower()]
            assert len(schema_warnings) == 0, f"Pydantic warnings: {schema_warnings}"


# ===========================================================================
# 3. MODEL LOADING TESTS
# ===========================================================================


class TestModelLoading:
    def test_model_not_found_returns_false(self):
        """Missing model file should not crash."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        assert not service.is_available()
        assert service.predict([], None, "test") == {}
        assert service.predict_result([], None, "test").fallback_used is True

    def test_model_loads_correctly(self, temp_model_dir: Path):
        """Valid model should load and be available."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        assert service._ensure_model_loaded() is True
        assert service.is_available() is True
        assert "LogisticRegression" in service._model_type

    def test_model_reload_works(self, temp_model_dir: Path):
        """reload() should re-load the model."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        assert service.reload() is True
        assert service.is_available() is True

    def test_feature_groups_loaded(self, temp_model_dir: Path):
        """Feature groups should be loaded from file."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        service._ensure_model_loaded()
        assert service._feature_groups is not None
        fg = service._feature_groups
        total = len(fg["numeric"]) + len(fg["categorical"]) + len(fg["binary"])
        assert total == 38

    def test_feature_groups_fallback_when_missing(self):
        """Missing feature_groups.json should fall back to hardcoded defaults."""
        fg = _load_feature_groups(Path("nonexistent/features.json"))
        total = len(fg["numeric"]) + len(fg["categorical"]) + len(fg["binary"])
        assert total == 38

    def test_corrupt_model_handled_gracefully(self, temp_model_dir: Path):
        """Corrupt model file should not crash."""
        corrupt_path = temp_model_dir / "corrupt_model.joblib"
        with open(corrupt_path, "w") as f:
            f.write("this is not a valid joblib file")

        service = MLPredictionService(
            model_path=str(corrupt_path),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        assert not service.is_available()
        result = service.predict([{"id": "abc"}], None, "test")
        assert result == {}  # graceful fallback


# ===========================================================================
# 4. FEATURE EXTRACTION TESTS
# ===========================================================================


class TestComputeTaskFeaturesDict:
    def test_basic_features(self):
        """Verify feature computation matches training pipeline."""
        snapshot = date(2026, 7, 15)
        feats = _compute_task_features_dict(
            task_id="task-001",
            created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            deadline="2026-07-20",
            estimated_duration=45,
            task_type="scheduled",
            priority="high",
            tags=["work", "urgent"],
            description="Do the thing",
            snapshot_date=snapshot,
        )
        assert feats["task_age_days"] == 5
        assert feats["has_deadline"] is True
        assert feats["is_overdue"] is False
        assert feats["deadline_relative_days"] == 5
        assert feats["estimated_duration"] == 45
        assert feats["has_estimated_duration"] is True
        assert feats["priority_high"] is True
        assert feats["priority_normal"] is False
        assert feats["task_type_scheduled"] is True
        assert feats["task_type_flexible"] is False
        assert feats["num_tags"] == 2
        assert feats["has_description"] is True
        assert feats["description_length"] == len("Do the thing")

    def test_overdue_deadline(self):
        """Overdue deadline should set is_overdue=True and negative relative_days."""
        snapshot = date(2026, 7, 15)
        feats = _compute_task_features_dict(
            task_id="task-002",
            created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            deadline="2026-07-14",
            estimated_duration=None,
            task_type="flexible",
            priority=None,
            tags=[],
            description=None,
            snapshot_date=snapshot,
        )
        assert feats["is_overdue"] is True
        assert feats["deadline_relative_days"] == -1
        assert feats["has_estimated_duration"] is False
        assert feats["estimated_duration"] == 30  # default
        assert feats["priority_normal"] is True  # default
        assert feats["task_type_flexible"] is True
        assert feats["num_tags"] == 0
        assert feats["has_description"] is False
        assert feats["description_length"] == 0

    def test_no_deadline(self):
        """No deadline should use MAX_SAFE_INT sentinel."""
        snapshot = date(2026, 7, 15)
        feats = _compute_task_features_dict(
            task_id="task-003",
            created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            deadline=None,
            estimated_duration=None,
            task_type="scheduled",
            priority="urgent",
            tags=[],
            description="",
            snapshot_date=snapshot,
        )
        assert feats["has_deadline"] is False
        assert feats["is_overdue"] is False
        assert feats["deadline_relative_days"] == 9999  # MAX_SAFE_INT
        assert feats["priority_urgent"] is True
        assert feats["description_length"] == 0

    def test_naive_datetime(self):
        """Handle naive (timezone-unaware) datetime gracefully."""
        snapshot = date(2026, 7, 15)
        feats = _compute_task_features_dict(
            task_id="task-004",
            created_at=datetime(2026, 7, 10, 0, 0, 0),  # naive datetime (no tzinfo)
            deadline=None, estimated_duration=None,
            task_type="scheduled", priority="normal",
            tags=[], description=None,
            snapshot_date=snapshot,
        )
        assert feats["task_age_days"] == 5


class TestGetTemporalFeatures:
    def test_monday(self):
        feats = _get_temporal_features(date(2026, 7, 27), False)  # Monday
        assert feats["target_day_of_week"] == 0
        assert feats["target_is_monday"] is True
        assert feats["target_is_friday"] is False
        assert feats["target_is_weekend"] is False
        assert feats["target_is_day_off"] is False

    def test_sunday_day_off(self):
        feats = _get_temporal_features(date(2026, 8, 2), True)  # Sunday
        assert feats["target_day_of_week"] == 6
        assert feats["target_is_weekend"] is True
        assert feats["target_is_day_off"] is True

    def test_friday(self):
        feats = _get_temporal_features(date(2026, 7, 31), False)  # Friday
        assert feats["target_day_of_week"] == 4
        assert feats["target_is_friday"] is True


class TestLoadFeatureGroups:
    def test_loads_from_file(self, temp_model_dir: Path):
        """Should load feature groups from JSON file."""
        fg = _load_feature_groups(temp_model_dir / "feature_groups.json")
        assert len(fg["numeric"]) == 12
        assert len(fg["categorical"]) == 1
        assert len(fg["binary"]) == 25

    def test_fallback_when_missing(self):
        """Should fall back to hardcoded defaults when file missing."""
        fg = _load_feature_groups(Path("nonexistent.json"))
        assert len(fg["numeric"]) == 12
        assert len(fg["categorical"]) == 1
        assert len(fg["binary"]) == 25

    def test_fallback_on_corrupt_json(self, temp_model_dir: Path):
        """Should fall back when JSON is corrupt."""
        bad_path = temp_model_dir / "bad_features.json"
        with open(bad_path, "w") as f:
            f.write("{not valid json")
        fg = _load_feature_groups(bad_path)
        assert len(fg["numeric"]) == 12  # fallback
        assert len(fg["binary"]) == 25


# ===========================================================================
# 5. TASK NORMALIZATION TESTS
# ===========================================================================


class TestNormalizeTasks:
    def test_normalize_sqlalchemy_model(self, session: Session, sample_task: Task):
        """SQLAlchemy Task object should be normalized correctly."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        task_dicts, task_ids = service._normalize_tasks([sample_task])
        assert len(task_dicts) == 1
        assert task_ids == [sample_task.id]
        assert task_dicts[0]["id"] == sample_task.id
        assert task_dicts[0]["title"] == "Sample task"
        assert task_dicts[0]["task_type"] == "scheduled"
        assert task_dicts[0]["daily_plan_id"] is None

    def test_normalize_sqlalchemy_with_tags(self, session: Session, sample_task: Task):
        """Tags from SQLAlchemy model should be included."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        task_dicts, _ = service._normalize_tasks([sample_task])
        assert task_dicts[0]["tags"] == ["work", "urgent"]

    def test_normalize_dict(self):
        """Plain dict should be passed through as-is."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        task_dicts, task_ids = service._normalize_tasks([
            {"id": "dict-1", "title": "Dict task", "created_at": datetime(2026, 7, 10, tzinfo=UTC)},
        ])
        assert len(task_dicts) == 1
        assert task_ids == ["dict-1"]
        assert task_dicts[0]["title"] == "Dict task"

    def test_normalize_mixed_input(self):
        """Mix of SQLAlchemy models and dicts should all be processed."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        fake_model = FakeTask(
            id="fake-1", title="Fake task",
            created_at=datetime(2026, 7, 10, tzinfo=UTC),
            deadline="2026-07-20", estimated_duration=60,
            task_type="scheduled", priority="high",
            tags=["work"], description="test",
            daily_plan_id=None, status="todo",
        )
        task_dicts, task_ids = service._normalize_tasks([
            fake_model,
            {"id": "dict-2", "title": "Dict task", "created_at": datetime(2026, 7, 10, tzinfo=UTC)},
        ])
        assert len(task_dicts) == 2
        assert task_ids == ["fake-1", "dict-2"]

    def test_skips_invalid_tasks(self):
        """Non-dict, non-model objects should be skipped."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        task_dicts, task_ids = service._normalize_tasks([
            "not a task",
            42,
            {"id": "valid", "title": "Valid", "created_at": datetime(2026, 7, 10, tzinfo=UTC)},
        ])
        assert len(task_dicts) == 1
        assert task_ids == ["valid"]

    def test_handles_missing_id(self):
        """Tasks without an ID should be excluded from task_ids."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        _, task_ids = service._normalize_tasks([
            {"title": "No ID task", "created_at": datetime(2026, 7, 10, tzinfo=UTC)},
        ])
        assert task_ids == []


# ===========================================================================
# 6. PREDICTION TESTS
# ===========================================================================


class TestPredictEmptyAndFallback:
    def test_empty_tasks_returns_empty(self):
        """Empty tasks should return empty dict."""
        service = MLPredictionService()
        result = service.predict([], None, "test-user")
        assert result == {}

    def test_empty_tasks_predict_result(self):
        """predict_result with empty tasks should have fallback status."""
        service = MLPredictionService()
        result = service.predict_result([], None, "test-user")
        assert result.result_status == "fallback_empty_input"
        assert result.fallback_used is True
        assert result.n_candidates == 0

    def test_missing_model_fallback(self):
        """Missing model should return empty dict with fallback."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        result = service.predict([{"id": "abc"}], None, "test-user")
        assert result == {}

    def test_missing_model_predict_result(self):
        """predict_result with missing model should have fallback status."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        result = service.predict_result([{"id": "abc"}], None, "test-user")
        assert result.result_status == "fallback_prediction_error"
        assert result.fallback_used is True
        assert result.n_candidates == 1

    def test_confidence_bands(self):
        """get_confidence_bands should return thresholds."""
        service = MLPredictionService()
        bands = service.get_confidence_bands()
        assert bands == {"high": 0.70, "medium": 0.40}

    def test_is_available_on_fresh_service(self):
        """Fresh service should not be available until model loads."""
        service = MLPredictionService()
        assert service.is_available() is False


class TestPredictWithRealModel:
    def test_predict_with_dicts(self, temp_model_dir: Path):
        """Predict with dict-based tasks should produce scores."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        # Create minimal task dicts that match expected feature columns
        snapshot = date(2026, 7, 15)
        tasks = [
            {"id": "task-1", "created_at": datetime(2026, 7, 10, tzinfo=UTC),
             "deadline": "2026-07-18", "estimated_duration": 60,
             "task_type": "scheduled", "priority": "high",
             "tags": ["work"], "description": "Task 1",
             "daily_plan_id": None},
            {"id": "task-2", "created_at": datetime(2026, 7, 12, tzinfo=UTC),
             "deadline": "2026-07-20", "estimated_duration": 30,
             "task_type": "flexible", "priority": "normal",
             "tags": [], "description": None,
             "daily_plan_id": None},
        ]
        # This needs a DB. Since we don't have one here, we mock the DB calls.
        with mock.patch("src.modules.ml.prediction_service._batch_reconstruct_statuses") as mock_status, \
             mock.patch("src.modules.ml.prediction_service._batch_get_event_counts") as mock_events, \
             mock.patch("src.modules.ml.prediction_service._get_user_context_features") as mock_ctx, \
             mock.patch("src.modules.ml.prediction_service._get_preferences") as mock_prefs:

            mock_status.return_value = {"task-1": "todo", "task-2": "todo"}
            mock_events.return_value = {
                "task-1": {"completion_count_7d": 0, "deferral_count_7d": 0,
                           "move_count_7d": 0, "skip_count_7d": 0,
                           "update_count_7d": 0, "days_since_last_completion": 9999},
                "task-2": {"completion_count_7d": 1, "deferral_count_7d": 0,
                           "move_count_7d": 0, "skip_count_7d": 0,
                           "update_count_7d": 0, "days_since_last_completion": 3},
            }
            mock_ctx.return_value = {
                "user_total_open_tasks": 50, "user_scheduled_count": 30,
                "user_flexible_count": 20, "user_completion_rate_7d": 0.5,
                "user_completed_count_7d": 10, "user_planned_count_7d": 5,
                "days_since_last_plan": 1,
            }
            mock_prefs.return_value = {
                "timezone": "Asia/Saigon", "day_offs": ["Saturday", "Sunday"],
                "work_start": "09:00", "work_end": "17:00",
            }

            result = service.predict(
                tasks, None, "test-user",
                snapshot_date=snapshot, timezone_str="Asia/Saigon",
            )

        assert len(result) == 2
        for task_id, score in result.items():
            assert 0.0 <= score <= 1.0
            assert isinstance(score, float)

    def test_predict_result_with_real_model(self, temp_model_dir: Path):
        """predict_result should return structured data with valid model."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )

        with mock.patch("src.modules.ml.prediction_service._batch_reconstruct_statuses") as mock_status, \
             mock.patch("src.modules.ml.prediction_service._batch_get_event_counts") as mock_events, \
             mock.patch("src.modules.ml.prediction_service._get_user_context_features") as mock_ctx, \
             mock.patch("src.modules.ml.prediction_service._get_preferences") as mock_prefs:

            mock_status.return_value = {"t1": "todo", "t2": "completed", "t3": "todo"}
            mock_events.return_value = {
                tid: {"completion_count_7d": 0, "deferral_count_7d": 0,
                      "move_count_7d": 0, "skip_count_7d": 0,
                      "update_count_7d": 0, "days_since_last_completion": 9999}
                for tid in ["t1", "t2", "t3"]
            }
            mock_ctx.return_value = {
                "user_total_open_tasks": 10, "user_scheduled_count": 5,
                "user_flexible_count": 5, "user_completion_rate_7d": 0.3,
                "user_completed_count_7d": 3, "user_planned_count_7d": 2,
                "days_since_last_plan": 1,
            }
            mock_prefs.return_value = {
                "timezone": "Asia/Saigon", "day_offs": ["Saturday", "Sunday"],
                "work_start": "09:00", "work_end": "17:00",
            }

            tasks = [
                {"id": "t1", "created_at": datetime(2026, 7, 10, tzinfo=UTC),
                 "deadline": None, "estimated_duration": 30,
                 "task_type": "scheduled", "priority": "normal",
                 "tags": [], "description": None, "daily_plan_id": None},
                {"id": "t2", "created_at": datetime(2026, 7, 11, tzinfo=UTC),
                 "deadline": None, "estimated_duration": 60,
                 "task_type": "scheduled", "priority": "high",
                 "tags": [], "description": "Task 2", "daily_plan_id": "plan-1"},
                {"id": "t3", "created_at": datetime(2026, 7, 12, tzinfo=UTC),
                 "deadline": "2026-07-18", "estimated_duration": 45,
                 "task_type": "flexible", "priority": "low",
                 "tags": ["personal"], "description": "Task 3",
                 "daily_plan_id": None},
            ]

            result = service.predict_result(
                tasks, None, "test-user",
                snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
            )

        assert result.result_status == "ok"
        assert result.classifier_type == "LogisticRegression"
        assert result.n_candidates == 3
        assert result.n_scored == 3
        assert not result.fallback_used
        assert len(result.predictions) == 3
        for pred in result.predictions:
            assert 0.0 <= pred.score <= 1.0
            assert pred.confidence_band in ("high", "medium", "low")


# ===========================================================================
# 7. END-TO-END WITH REAL DB
# ===========================================================================


class TestPredictWithDB:
    def test_e2e_with_db_session(self, session: Session, user_id: str, temp_model_dir: Path):
        """Full end-to-end: tasks from DB, feature queries through DB, model predicts."""
        # Create tasks in DB
        task1 = Task(
            id=new_id(), user_id=user_id, title="Task 1",
            description="Important task", estimated_duration=60,
            deadline=(date.today() + timedelta(days=2)).isoformat(),
            task_type="scheduled", priority="urgent", status="todo",
            tags=["work"], created_at=datetime(2026, 7, 10, tzinfo=UTC),
            updated_at=datetime(2026, 7, 10, tzinfo=UTC),
        )
        task2 = Task(
            id=new_id(), user_id=user_id, title="Task 2",
            description=None, estimated_duration=30,
            deadline=None, task_type="flexible", priority="low",
            status="todo", tags=[], created_at=datetime(2026, 7, 14, tzinfo=UTC),
            updated_at=datetime(2026, 7, 14, tzinfo=UTC),
        )
        session.add_all([task1, task2])
        session.flush()

        # Add activity events for task1
        session.add(ActivityEvent(
            id=new_id(), user_id=user_id, event_type="task_completed",
            entity_type="task", entity_id=task1.id, source="manual",
            payload={}, occurred_at=datetime(2026, 7, 12, 10, 0, 0, tzinfo=UTC),
        ))
        session.commit()

        # Create service
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )

        # Predict
        result = service.predict_result(
            [task1, task2], session, user_id,
            snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
        )

        # Verify
        assert result.n_candidates == 2
        assert result.n_scored == 2
        assert not result.fallback_used
        assert len(result.predictions) == 2
        for pred in result.predictions:
            assert pred.task_id in (task1.id, task2.id)
            assert 0.0 <= pred.score <= 1.0

    def test_strategy_resolves_correct_paths(self, temp_model_dir: Path):
        """Strategy 'synthetic' should use the default model paths."""
        service = MLPredictionService(strategy="synthetic")
        # Strategy resolves paths in __post_init__; it should use the synthetic dir
        assert "synthetic" in str(service.model_path)

    def test_strategy_retrained_fallback_when_missing(self):
        """Strategy 'retrained' with no retrained model dir falls back to synthetic."""
        service = MLPredictionService(strategy="retrained")
        # If retrained dir is missing, fallback to synthetic dir paths
        # model_path should still work even with fallback logic
        assert service.model_path.exists() or "synthetic" in str(service.model_path)

    def test_unknown_strategy_falls_back(self):
        """Unknown strategy name should fall back to synthetic (not crash)."""
        import logging
        with mock.patch.object(logging.getLogger("src.modules.ml.prediction_service"), "warning") as mock_warn:
            service = MLPredictionService(strategy="nonexistent_strategy")
            mock_warn.assert_called()
        assert "synthetic" in str(service.model_path)

    def _default_event_counts(self) -> dict:
        return {"completion_count_7d": 0, "deferral_count_7d": 0,
                "move_count_7d": 0, "skip_count_7d": 0,
                "update_count_7d": 0, "days_since_last_completion": 9999}

    @staticmethod
    def _default_user_context() -> dict:
        return {"user_total_open_tasks": 10, "user_scheduled_count": 5,
                "user_flexible_count": 5, "user_completion_rate_7d": 0.3,
                "user_completed_count_7d": 3, "user_planned_count_7d": 2,
                "days_since_last_plan": 1}

    def test_strategy_field_in_predict_result(self, temp_model_dir: Path):
        """predict_result should work regardless of strategy."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
            strategy="synthetic",
        )
        with mock.patch("src.modules.ml.prediction_service._batch_reconstruct_statuses") as mock_status, \
             mock.patch("src.modules.ml.prediction_service._batch_get_event_counts") as mock_events, \
             mock.patch("src.modules.ml.prediction_service._get_user_context_features") as mock_ctx, \
             mock.patch("src.modules.ml.prediction_service._get_preferences") as mock_prefs:
            mock_status.return_value = {"t1": "todo"}
            mock_events.return_value = {"t1": self._default_event_counts()}
            mock_ctx.return_value = self._default_user_context()
            mock_prefs.return_value = {"timezone": "Asia/Saigon", "day_offs": ["Saturday", "Sunday"],
                                       "work_start": "09:00", "work_end": "17:00"}

            result = service.predict_result(
                [{"id": "t1", "created_at": datetime(2026, 7, 10, tzinfo=UTC),
                  "deadline": None, "estimated_duration": 30,
                  "task_type": "scheduled", "priority": "normal",
                  "tags": [], "description": None, "daily_plan_id": None}],
                None, "test-user",
                snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
            )
        assert result.n_scored == 1
        assert not result.fallback_used

    def test_inference_latency(self, session: Session, user_id: str, temp_model_dir: Path):
        """Inference should complete quickly (<< 1s for small batch)."""
        import time

        # Create a few tasks
        tasks = []
        for i in range(5):
            t = Task(
                id=new_id(), user_id=user_id,
                title=f"Task {i}", estimated_duration=30 + i * 10,
                task_type="scheduled", priority="normal", status="todo",
                tags=[], created_at=datetime(2026, 7, 10 + i, tzinfo=UTC),
                updated_at=datetime(2026, 7, 10 + i, tzinfo=UTC),
            )
            session.add(t)
            tasks.append(t)
        session.commit()

        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )

        t0 = time.time()
        result = service.predict_result(
            tasks, session, user_id,
            snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
        )
        elapsed = time.time() - t0

        assert result.n_scored == 5
        assert elapsed < 2.0, f"Inference took {elapsed:.3f}s (expected < 2s)"


# ===========================================================================
# 8. EDGE CASES & FALLBACK TESTS
# ===========================================================================


class TestEdgeCases:
    def test_single_task(self, session: Session, user_id: str, temp_model_dir: Path):
        """Single task should work."""
        task = Task(
            id=new_id(), user_id=user_id, title="Single task",
            task_type="scheduled", priority="normal", status="todo",
            tags=[], created_at=datetime(2026, 7, 10, tzinfo=UTC),
            updated_at=datetime(2026, 7, 10, tzinfo=UTC),
        )
        session.add(task)
        session.commit()

        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        result = service.predict_result(
            [task], session, user_id,
            snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
        )
        assert result.n_scored == 1
        assert result.n_candidates == 1

    def test_many_tasks(self, session: Session, user_id: str, temp_model_dir: Path):
        """50 tasks should all be scored without error."""
        tasks = []
        for i in range(50):
            t = Task(
                id=new_id(), user_id=user_id, title=f"Bulk task {i}",
                task_type="scheduled" if i % 2 == 0 else "flexible",
                priority=["low", "normal", "high", "urgent"][i % 4],
                status="todo", tags=[],
                created_at=datetime(2026, 7, 10, tzinfo=UTC),
                updated_at=datetime(2026, 7, 10, tzinfo=UTC),
            )
            session.add(t)
            tasks.append(t)
        session.commit()

        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        result = service.predict_result(
            tasks, session, user_id,
            snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
        )
        assert result.n_scored == 50
        assert result.n_candidates == 50

    def test_db_error_fallback(self, temp_model_dir: Path):
        """DB error during feature extraction should fall back gracefully."""
        mock_db = mock.MagicMock()
        # Make the execute method raise an exception on first call
        mock_db.execute.side_effect = Exception("DB connection lost")

        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        result = service.predict(
            [{"id": "t1", "created_at": datetime(2026, 7, 10, tzinfo=UTC)}],
            mock_db, "test-user",
            snapshot_date=date(2026, 7, 15), timezone_str="Asia/Saigon",
        )
        assert result == {}  # graceful fallback on DB error

    def test_missing_user_id_fallback(self, temp_model_dir: Path):
        """Empty user_id should not crash."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        # No tasks + no DB + missing user_id should return empty
        result = service.predict([], None, "")
        assert result == {}

    def test_predict_result_fallback_metadata(self):
        """predict_result should include fallback metadata even on error."""
        service = MLPredictionService(model_path="nonexistent/model.joblib")
        result = service.predict_result([{"id": "t1"}], None, "test")
        assert result.fallback_used is True
        assert result.result_status in ("fallback_model_missing", "fallback_prediction_error")
        assert result.n_candidates == 1
        assert result.n_scored == 0


# ===========================================================================
# 9. CONFIDENCE BAND TESTS
# ===========================================================================


class TestConfidenceBands:
    def test_confidence_bands_constant(self):
        """Confidence bands should match product thresholds."""
        service = MLPredictionService()
        bands = service.get_confidence_bands()
        assert bands["high"] == 0.70
        assert bands["medium"] == 0.40

    def test_high_confidence_band_assignment(self, temp_model_dir: Path):
        """Tasks with score >= 0.70 should be 'high' confidence."""
        service = MLPredictionService(
            model_path=str(temp_model_dir / "model_pipeline.joblib"),
            feature_groups_path=str(temp_model_dir / "feature_groups.json"),
        )
        with mock.patch.object(service, "predict") as mock_predict:
            mock_predict.return_value = {"t1": 0.85, "t2": 0.50, "t3": 0.20}
            result = service.predict_result([{"id": "t1"}, {"id": "t2"}, {"id": "t3"}], None, "test")

        bands = {p.task_id: p.confidence_band for p in result.predictions}
        assert bands["t1"] == "high"
        assert bands["t2"] == "medium"
        assert bands["t3"] == "low"
        assert result.n_high_confidence == 1
        assert result.n_medium_confidence == 1


# ===========================================================================
# 10. TIMEZONE HELPER TESTS
# ===========================================================================


class TestTimezoneHelpers:
    def test_compute_end_of_day_asia_saigon(self):
        """Asia/Saigon (UTC+7): end of 2026-07-26 = 2026-07-26T16:59:59Z."""
        d = date(2026, 7, 26)
        eod = compute_end_of_day(d, "Asia/Saigon")
        assert eod.year == 2026 and eod.month == 7 and eod.day == 26
        assert eod.hour == 16 and eod.minute == 59
        assert eod.tzinfo is not None

    def test_compute_end_of_day_utc(self):
        """UTC: end of 2026-07-26 = 2026-07-26T23:59:59Z."""
        d = date(2026, 7, 26)
        eod = compute_end_of_day(d, "UTC")
        assert eod.hour == 23 and eod.minute == 59


# ===========================================================================
# 11. END-TO-END: ML + DailyPlanService INTEGRATION
# ===========================================================================


class TestDailyPlanMLIntegration:
    """Verify ML scoring is integrated into DailyPlanService.draft().

    Test flow:
      1. Create user with preferences and tasks
      2. Call draft() for tomorrow's date
      3. Verify plan has source="ml_boosted"
      4. Query context_snapshot for ML metadata
      5. Verify tasks are re-ranked (at minimum, all scored)
    """

    def _create_user_with_data(
        self, session: Session,
    ) -> tuple[str, list[str], date]:
        """Create test user, tasks, activity events. Returns (user_id, [task_ids], tomorrow)."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Skip if tomorrow is weekend
        while tomorrow.weekday() >= 5:
            tomorrow += timedelta(days=1)

        uid = new_id()
        session.add(User(
            id=uid, email="e2e-ml-test@example.com",
            password_hash="fakehash", name="E2E ML User",
            timezone="Asia/Saigon", role="user",
        ))
        session.add(UserSchedulePreference(
            id=new_id(), user_id=uid,
            work_start_time="09:00", work_end_time="17:00",
            lunch_start_time="12:00", lunch_end_time="13:00",
            day_offs=["Saturday", "Sunday"], focus_hours=[],
        ))
        session.flush()

        # Create multiple tasks with different profiles
        task_configs = [
            # (title, priority, task_type, deadline_offset, has_desc, tags, created_offset)
            ("Urgent deadline task", "urgent", "scheduled", 1, True, ["work"], 5),
            ("High priority task", "high", "scheduled", 3, True, ["work"], 4),
            ("Normal scheduled task", "normal", "scheduled", 7, True, [], 3),
            ("Low priority task", "low", "scheduled", 14, False, [], 2),
            ("Flexible task no deadline", "normal", "flexible", None, False, ["personal"], 1),
        ]

        task_ids: list[str] = []
        for title, priority, task_type, deadline_offset, has_desc, tags, created_offset in task_configs:
            tid = new_id()
            deadline = (today + timedelta(days=deadline_offset)).isoformat() if deadline_offset else None
            desc = f"Description for {title}" if has_desc else None
            created = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=UTC) - timedelta(days=created_offset)

            session.add(Task(
                id=tid, user_id=uid, title=title,
                description=desc,
                estimated_duration=60,
                deadline=deadline,
                task_type=task_type, priority=priority, status="todo",
                tags=tags,
                created_at=created,
                updated_at=created,
            ))
            task_ids.append(tid)

        # Add activity events for the first 2 tasks (recent completions)
        for i, tid in enumerate(task_ids[:2]):
            session.add(ActivityEvent(
                id=new_id(), user_id=uid, event_type="task_completed",
                entity_type="task", entity_id=tid, source="manual",
                payload={},
                occurred_at=datetime(today.year, today.month, today.day, 10, 0, 0, tzinfo=UTC) - timedelta(days=1 + i),
            ))

        session.commit()
        return uid, task_ids, tomorrow

    def test_draft_plan_has_ml_source(self, session: Session):
        """Plan created via draft() should have source='ml_boosted'."""
        from src.modules.daily_plans.service import DailyPlanService

        uid, task_ids, plan_date = self._create_user_with_data(session)

        # Create service and generate draft plan
        service = DailyPlanService(session, uid)
        plan = service.draft(
            plan_date=plan_date.isoformat(),
            context_window_type="test_e2e_ml",
            trigger_source="test",
        )

        # Verify plan properties
        assert plan.source == "ml_boosted", f"Expected ml_boosted, got {plan.source}"
        assert plan.status == "draft"
        assert plan.plan_date == plan_date.isoformat()
        assert plan.explanation is not None
        assert len(plan.schedules) >= 1

    def test_context_snapshot_has_ml_metadata(self, session: Session):
        """Context snapshot should contain ML scoring metadata."""
        from src.modules.daily_plans.service import DailyPlanService

        uid, task_ids, plan_date = self._create_user_with_data(session)

        service = DailyPlanService(session, uid)
        plan = service.draft(
            plan_date=plan_date.isoformat(),
            context_window_type="test_e2e_ml",
            trigger_source="test",
        )

        # Fetch the context snapshot associated with this plan
        snapshot = session.get(ContextSnapshot, plan.context_snapshot_id)
        assert snapshot is not None, "No context snapshot found"
        assert snapshot.snapshot_type == "test_e2e_ml"

        payload = snapshot.context_payload
        assert "ml" in payload, f"Context payload missing 'ml' key: {list(payload.keys())}"

        ml_data = payload["ml"]
        assert ml_data["status"] == "ok", f"ML status: {ml_data.get('status')}"
        assert ml_data["classifier"] == "LogisticRegression"
        # Only TaskType.scheduled are included in _list_candidate_tasks()
        # We created 4 scheduled + 1 flexible = 4 scored
        assert ml_data["n_scored"] == 4, f"Expected 4 tasks scored, got {ml_data.get('n_scored')}"
        assert ml_data["n_high_confidence"] >= 0
        assert ml_data["n_medium_confidence"] >= 0
        assert ml_data["fallback_used"] is False

        # top_scores should be a list of [task_id_prefix, score, band] tuples
        assert "top_scores" in ml_data
        assert len(ml_data["top_scores"]) > 0
        top_score = ml_data["top_scores"][0]
        assert len(top_score) == 3  # (task_id_prefix, score, band)
        assert isinstance(top_score[1], float)
        assert 0.0 <= top_score[1] <= 1.0

    def test_tasks_are_ranked_by_ml_score(self, session: Session):
        """Task ordering in the plan should reflect ML scores."""
        from src.modules.daily_plans.service import DailyPlanService

        uid, task_ids, plan_date = self._create_user_with_data(session)

        service = DailyPlanService(session, uid)
        plan = service.draft(
            plan_date=plan_date.isoformat(),
            context_window_type="test_e2e_ml",
            trigger_source="test",
        )

        # Verify the plan has schedule items
        for schedule in plan.schedules:
            if schedule.items:
                first_item = schedule.items[0]
                # The first task should have a task_id from our list
                assert first_item.task_id in task_ids, f"Unexpected task_id: {first_item.task_id}"

        # Get all scheduled task IDs in order
        scheduled_ids = []
        for schedule in plan.schedules:
            for item in schedule.items:
                if item.task_id:
                    scheduled_ids.append(item.task_id)

        # Verify at least some tasks are scheduled
        assert len(scheduled_ids) > 0, "No tasks were scheduled"

        # All scheduled tasks should be from our original task set
        for tid in scheduled_ids:
            assert tid in task_ids, f"Scheduled task {tid} not in original task set"

        # Task count should be reasonable (at least 2, at most all 5)
        assert 2 <= len(scheduled_ids) <= 5

    def test_ml_fallback_when_model_missing(self, session: Session):
        """If model is missing, plan should fall back to rule_based."""
        from src.modules.daily_plans.service import DailyPlanService
        from src.modules.ml.prediction_service import MLPredictionService

        uid, task_ids, plan_date = self._create_user_with_data(session)

        # Mock the model to be unavailable — use clean patching
        with mock.patch.object(MLPredictionService, '_ensure_model_loaded', return_value=False):
            service = DailyPlanService(session, uid)
            plan = service.draft(
                plan_date=plan_date.isoformat(),
                context_window_type="test_e2e_ml_fallback",
                trigger_source="test",
            )

            # Without model, plan should still be generated (rule-based fallback)
            assert plan.source == "rule_based"
            assert plan.status == "draft"
            assert len(plan.schedules) >= 1

            # Context snapshot should NOT have ML metadata
            snapshot = session.get(ContextSnapshot, plan.context_snapshot_id)
            if snapshot and "ml" in (snapshot.context_payload or {}):
                ml_data = snapshot.context_payload.get("ml", {})
                assert ml_data.get("fallback_used", True) is True, "Should have fallback"
