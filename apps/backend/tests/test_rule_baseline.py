"""
Unit tests for rule_baseline.py (Phase 4 rule-based comparison).

Tests:
  - Individual scoring functions with various edge cases
  - Composite rule_score function
  - Score breakdown
  - Metric computation reuse
  - Comparison runner end-to-end
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

from scripts.rule_baseline import (
    WEIGHTS,
    _score_activity_momentum,
    _score_deadline_urgency,
    _score_priority,
    _score_recent_planning,
    _score_task_type,
    _score_temporal,
    _score_breakdown,
    compute_rule_scores,
    rule_score,
    run_comparison,
)


def _row(**overrides: object) -> dict[str, object]:
    """Build a default row dict with overrides for testing."""
    defaults: dict[str, object] = {
        "has_deadline": False,
        "deadline_relative_days": 9999,
        "is_overdue": False,
        "priority_urgent": False,
        "priority_high": False,
        "priority_low": False,
        "has_plan_for_past_or_today": False,
        "days_since_last_plan": 9999,
        "completion_count_7d": 0,
        "deferral_count_7d": 0,
        "task_type_scheduled": True,
        "target_is_monday": False,
        "target_is_friday": False,
        "target_is_weekend": False,
        "target_is_day_off": False,
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# 1. Deadline urgency scoring
# ===========================================================================


class TestScoreDeadlineUrgency:
    def test_overdue_is_max(self):
        assert _score_deadline_urgency(_row(is_overdue=True)) == 1.0

    def test_today_deadline_is_high(self):
        assert _score_deadline_urgency(_row(has_deadline=True, deadline_relative_days=0)) == 1.0

    def test_no_deadline_is_low(self):
        assert _score_deadline_urgency(_row()) == 0.2

    def test_future_deadline_decays(self):
        s1 = _score_deadline_urgency(_row(has_deadline=True, deadline_relative_days=1))
        s7 = _score_deadline_urgency(_row(has_deadline=True, deadline_relative_days=7))
        assert s1 > s7, "Closer deadline should score higher"
        assert 0 < s1 <= 0.9

    def test_sentinel_9999_returns_low(self):
        assert _score_deadline_urgency(_row(has_deadline=True, deadline_relative_days=9999)) == 0.2


# ===========================================================================
# 2. Priority scoring
# ===========================================================================


class TestScorePriority:
    def test_urgent_is_max(self):
        assert _score_priority(_row(priority_urgent=True)) == 1.0

    def test_high_is_08(self):
        assert _score_priority(_row(priority_high=True)) == 0.8

    def test_normal_is_05(self):
        assert _score_priority(_row()) == 0.5  # default

    def test_low_is_02(self):
        assert _score_priority(_row(priority_low=True)) == 0.2

    def test_urgent_overrides_high(self):
        """When both urgent and high are true, urgent wins."""
        result = _score_priority(_row(priority_urgent=True, priority_high=True))
        assert result == 1.0

    def test_high_overrides_low(self):
        """Priority hierarchy is respected."""
        result = _score_priority(_row(priority_high=True, priority_low=True))
        assert result == 0.8  # high wins


# ===========================================================================
# 3. Recent planning scoring
# ===========================================================================


class TestScoreRecentPlanning:
    def test_has_plan_now_is_08(self):
        assert _score_recent_planning(_row(has_plan_for_past_or_today=True)) == 0.8

    def test_never_planned_is_zero(self):
        assert _score_recent_planning(_row()) == 0.0

    def test_recent_plan_decays(self):
        s1 = _score_recent_planning(_row(days_since_last_plan=1))
        s30 = _score_recent_planning(_row(days_since_last_plan=30))
        assert s1 > s30, "More recent plan should score higher"
        assert 0 < s1 <= 0.7

    def test_past_plan_outweighs_momentary_plan(self):
        """has_plan_for_past_or_today dominates recent planning history."""
        with_plan = _score_recent_planning(_row(has_plan_for_past_or_today=True))
        recent_only = _score_recent_planning(_row(days_since_last_plan=1))
        assert with_plan > recent_only


# ===========================================================================
# 4. Activity momentum scoring
# ===========================================================================


class TestScoreActivityMomentum:
    def test_no_activity_is_zero(self):
        assert _score_activity_momentum(_row()) == 0.0

    def test_completions_increase_score(self):
        s1 = _score_activity_momentum(_row(completion_count_7d=1))
        s5 = _score_activity_momentum(_row(completion_count_7d=5))
        assert s1 < s5
        assert s1 > 0.0

    def test_capped_at_1(self):
        # Way above cap
        s = _score_activity_momentum(_row(completion_count_7d=100))
        assert s <= 1.0

    def test_deferrals_also_count(self):
        s_base = _score_activity_momentum(_row(completion_count_7d=1))
        s_with_defer = _score_activity_momentum(_row(completion_count_7d=1, deferral_count_7d=2))
        assert s_with_defer > s_base


# ===========================================================================
# 5. Task type scoring
# ===========================================================================


class TestScoreTaskType:
    def test_scheduled_is_07(self):
        assert _score_task_type(_row(task_type_scheduled=True)) == 0.7

    def test_flexible_is_03(self):
        assert _score_task_type(_row(task_type_scheduled=False)) == 0.3


# ===========================================================================
# 6. Temporal scoring
# ===========================================================================


class TestScoreTemporal:
    def test_monday_bonus(self):
        mon = _score_temporal(_row(target_is_monday=True))
        normal = _score_temporal(_row())
        assert mon > normal

    def test_weekend_penalty(self):
        weekend = _score_temporal(_row(target_is_weekend=True))
        normal = _score_temporal(_row())
        assert weekend < normal

    def test_day_off_penalty(self):
        day_off = _score_temporal(_row(target_is_day_off=True))
        normal = _score_temporal(_row())
        assert day_off < normal

    def test_clamped_to_range(self):
        """Score should never go below 0 or above 1."""
        # All bonuses
        s = _score_temporal(_row(
            target_is_monday=True,
            target_is_friday=True,
        ))
        assert 0.0 <= s <= 1.0

        # All penalties
        s = _score_temporal(_row(
            target_is_weekend=True,
            target_is_day_off=True,
        ))
        assert 0.0 <= s <= 1.0

    def test_friday_bonus(self):
        fri = _score_temporal(_row(target_is_friday=True))
        normal = _score_temporal(_row())
        assert fri > normal


# ===========================================================================
# 7. Composite score
# ===========================================================================


class TestRuleScore:
    def test_normal_task_mid_range(self):
        """A normal task with no special features should score mid-range."""
        s = rule_score(_row())
        assert 0.1 < s < 0.9

    def test_overdue_urgent_task_high(self):
        """An overdue urgent task should score high."""
        s = rule_score(_row(
            has_deadline=True,
            deadline_relative_days=-1,
            is_overdue=True,
            priority_urgent=True,
            has_plan_for_past_or_today=True,
        ))
        assert s > 0.5

    def test_low_priority_no_deadline_low(self):
        """A low-priority task with no deadline should score low."""
        s = rule_score(_row(
            priority_low=True,
            task_type_scheduled=False,
        ))
        assert s < 0.5

    def test_returns_float_between_0_and_1(self):
        s = rule_score(_row(
            has_deadline=True, deadline_relative_days=10,
            priority_high=True,
        ))
        assert 0.0 <= s <= 1.0

    def test_score_batch_consistent(self):
        """Scores computed individually should match batch compute."""
        rows = [
            _row(has_deadline=True, deadline_relative_days=1),
            _row(has_deadline=False),
            _row(is_overdue=True, priority_urgent=True),
        ]
        df = pd.DataFrame(rows)
        batch_scores = compute_rule_scores(df)
        individual_scores = [rule_score(r) for r in rows]
        assert np.allclose(batch_scores, individual_scores)


# ===========================================================================
# 8. Score breakdown
# ===========================================================================


class TestScoreBreakdown:
    def test_returns_all_components(self):
        row = _row(is_overdue=True, priority_urgent=True)
        breakdown = _score_breakdown(row)
        assert set(breakdown.keys()) == {
            "deadline_urgency", "priority", "recent_planning",
            "activity_momentum", "task_type", "temporal", "combined",
        }
        assert breakdown["deadline_urgency"] == 1.0
        assert breakdown["priority"] == 1.0
        assert 0.0 <= breakdown["combined"] <= 1.0


# ===========================================================================
# 9. End-to-end comparison
# ===========================================================================


class TestRunComparison:
    @pytest.fixture
    def df_with_labels(self) -> pd.DataFrame:
        """Dataset with some positive labels for meaningful comparison."""
        np.random.seed(42)
        n = 100

        dates = ["2026-07-10", "2026-07-11", "2026-07-12", "2026-07-13"]
        data: dict[str, list] = {
            "snapshot_date": np.random.choice(dates, n).tolist(),
            "target_date": ["2026-07-11"] * n,
            "user_id": ["user-001"] * n,
            "task_id": [f"task-{i:03d}" for i in range(n)],
            "task_title_hint": [f"Task {i}" for i in range(n)],
            "user_timezone": ["Asia/Saigon"] * n,
            "target_weekday_name": np.random.choice(
                ["Monday", "Tuesday", "Wednesday"], n
            ).tolist(),
            "status_at_d": ["todo"] * n,
            "task_age_days": np.random.randint(0, 20, n).tolist(),
            "deadline_relative_days": np.random.randint(-5, 15, n).tolist(),
            "description_length": np.random.randint(0, 200, n).tolist(),
            "user_total_open_tasks": np.random.randint(50, 500, n).tolist(),
            "user_scheduled_count": np.random.randint(30, 300, n).tolist(),
            "user_flexible_count": np.random.randint(0, 50, n).tolist(),
            "user_planned_count_7d": np.random.randint(0, 100, n).tolist(),
            "days_since_last_plan": np.random.randint(0, 30, n).tolist(),
            "days_since_last_completion": np.random.choice(
                [1, 3, 10, 9999], n
            ).tolist(),
            "estimated_duration": np.random.choice([30, 60, 90], n).tolist(),
            "has_deadline": np.random.choice([True, False], n).tolist(),
            "is_overdue": np.random.choice([True, False], n, p=[0.2, 0.8]).tolist(),
            "has_estimated_duration": [True] * n,
            "priority_urgent": np.random.choice([True, False], n, p=[0.1, 0.9]).tolist(),
            "priority_high": np.random.choice([True, False], n, p=[0.3, 0.7]).tolist(),
            "priority_normal": [False] * n,
            "priority_low": np.random.choice([True, False], n, p=[0.1, 0.9]).tolist(),
            "task_type_scheduled": np.random.choice([True, False], n, p=[0.7, 0.3]).tolist(),
            "task_type_flexible": [False] * n,
            "num_tags": np.random.randint(0, 5, n).tolist(),
            "has_description": np.random.choice([True, False], n).tolist(),
            "status_is_planned": [False] * n,
            "status_is_deferred": [False] * n,
            "status_is_skipped": [False] * n,
            "has_plan_for_past_or_today": np.random.choice([True, False], n).tolist(),
            "completion_count_7d": np.random.randint(0, 5, n).tolist(),
            "deferral_count_7d": np.random.randint(0, 3, n).tolist(),
            "move_count_7d": [0] * n,
            "skip_count_7d": [0] * n,
            "update_count_7d": [0] * n,
            "user_completed_count_7d": np.random.randint(0, 10, n).tolist(),
            "user_completion_rate_7d": np.random.uniform(0, 1, n).round(4).tolist(),
            "target_day_of_week": np.random.randint(0, 5, n).tolist(),
            "target_is_monday": [False] * n,
            "target_is_friday": [False] * n,
            "target_is_weekend": [False] * n,
            "target_is_day_off": [False] * n,
            "label": np.random.choice([0, 1], n, p=[0.8, 0.2]).tolist(),
        }
        df = pd.DataFrame(data)
        if df["label"].sum() == 0:
            df.loc[0, "label"] = 1
        return df

    def test_comparison_runs_end_to_end(self, df_with_labels: pd.DataFrame):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_comparison(
                df_with_labels,
                output_dir=tmpdir,
                train_snapshots=2,
            )
            assert "ml_metrics" in result
            assert "rule_metrics" in result
            assert "comparison_summary" in result
            assert result["ml_metrics"]["n_total"] > 0
            assert result["rule_metrics"]["n_total"] == result["ml_metrics"]["n_total"]

    def test_saves_comparison_report(self, df_with_labels: pd.DataFrame):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_comparison(df_with_labels, output_dir=tmpdir, train_snapshots=2)
            report_path = Path(tmpdir) / "comparison_report.json"
            assert report_path.exists()
            with open(report_path) as f:
                report = json.load(f)
            assert "ml" in report
            assert "rule_based" in report
            assert "comparison" in report
            assert "winner" in report["comparison"]

    def test_both_baselines_on_same_validation_set(
        self, df_with_labels: pd.DataFrame
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_comparison(
                df_with_labels,
                output_dir=tmpdir,
                train_snapshots=2,
            )
            assert (
                result["ml_metrics"]["n_total"]
                == result["rule_metrics"]["n_total"]
            )
            assert (
                result["ml_metrics"]["n_positive"]
                == result["rule_metrics"]["n_positive"]
            )
