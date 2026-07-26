"""
Unit tests for build_ml_dataset.py (snapshot extraction job).

Uses SQLite in-memory database with controlled test data.
Tests candidate filtering, label assignment, timezone handling,
feature extraction, and end-to-end snapshot building.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

# Ensure the backend src is on the path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set test environment BEFORE importing the module
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from src.core.config import get_settings

get_settings.cache_clear()

from src.db.base import Base
from src.db.models import (
    ActivityEvent,
    ContextSnapshot,
    DailyPlan,
    DaySummary,
    Schedule,
    ScheduleItem,
    Task,
    User,
    UserSchedulePreference,
)
from src.db.session import get_session_factory

# Import the functions to test (must be done after DB is configured)
from scripts.build_ml_dataset import (
    MAX_SAFE_INT,
    WEEKDAY_NAMES,
    _batch_get_event_counts,
    _batch_reconstruct_statuses,
    _build_rows_for_snapshot,
    _compute_task_features,
    _get_candidate_tasks,
    _get_label,
    _get_plan_for_date,
    _get_preferences,
    _get_temporal_features,
    _get_user_context_features,
    build_dataset,
    compute_end_of_day,
    date_from_iso,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine():
    """Create SQLite in-memory engine with foreign keys enabled."""
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Enable foreign key support in SQLite
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
    from src.db.models import new_id

    uid = new_id()
    user = User(
        id=uid,
        email="ml-test@example.com",
        password_hash="fakehash",
        name="ML Test User",
        timezone="Asia/Saigon",
        role="user",
    )
    session.add(user)
    session.commit()
    return uid


@pytest.fixture
def preferences(session: Session, user_id: str):
    """Create schedule preferences for the test user."""
    pref = UserSchedulePreference(
        user_id=user_id,
        work_start_time="09:00",
        work_end_time="17:00",
        lunch_start_time="12:00",
        lunch_end_time="13:00",
        day_offs=["Saturday", "Sunday"],
        focus_hours=[],
    )
    session.add(pref)
    session.commit()
    return pref


def _make_task(
    session: Session,
    user_id: str,
    *,
    title: str = "Test task",
    deadline: str | None = None,
    priority: str = "normal",
    task_type: str = "scheduled",
    status: str = "todo",
    estimated_duration: int = 60,
    tags: list[str] | None = None,
    completed_at: datetime | None = None,
    created_at: datetime | None = None,
    deleted_at: datetime | None = None,
    daily_plan_id: str | None = None,
) -> Task:
    """Helper to create a task with deterministic fields."""
    from src.db.models import new_id

    if created_at is None:
        created_at = datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC)
    if tags is None:
        tags = []

    task = Task(
        id=new_id(),
        user_id=user_id,
        title=title,
        deadline=deadline,
        priority=priority,
        task_type=task_type,
        status=status,
        estimated_duration=estimated_duration,
        tags=tags,
        completed_at=completed_at,
        created_at=created_at,
        updated_at=created_at,
        deleted_at=deleted_at,
        daily_plan_id=daily_plan_id,
    )
    session.add(task)
    session.flush()
    return task


def _make_plan(session: Session, user_id: str, plan_date: str, *, status: str = "confirmed") -> DailyPlan:
    """Helper to create a daily plan."""
    from src.db.models import new_id

    snap = ContextSnapshot(
        id=new_id(),
        user_id=user_id,
        snapshot_type="test",
        context_payload={},
    )
    plan = DailyPlan(
        id=new_id(),
        user_id=user_id,
        plan_date=plan_date,
        status=status,
        source="test",
        context_snapshot_id=snap.id,
        explanation="Test plan",
    )
    session.add_all([snap, plan])
    session.flush()
    return plan


def _make_schedule_item(
    session: Session, plan_id: str, task_id: str, *, start_time: str = "09:00", end_time: str = "10:00"
):
    """Helper to create a schedule item linking a task to a plan's schedule."""
    from src.db.models import new_id

    schedule = Schedule(
        id=new_id(),
        user_id=session.query(Task).filter(Task.id == task_id).first().user_id,
        daily_plan_id=plan_id,
        schedule_date="2026-07-11",
        schedule_type="day",
        source="test",
    )
    session.add(schedule)
    session.flush()

    item = ScheduleItem(
        id=new_id(),
        schedule_id=schedule.id,
        task_id=task_id,
        start_time=start_time,
        end_time=end_time,
        label="Test item",
        status="planned",
        source="test",
    )
    session.add(item)
    session.flush()
    return item


# ===========================================================================
# 1. TIMEZONE BOUNDARY TESTS
# ===========================================================================


class TestTimezoneBoundary:
    def test_compute_end_of_day_asia_saigon(self):
        """Asia/Saigon (UTC+7): end of 2026-07-26 = 2026-07-26T16:59:59Z"""
        d = date(2026, 7, 26)
        eod = compute_end_of_day(d, "Asia/Saigon")
        assert eod.year == 2026
        assert eod.month == 7
        assert eod.day == 26
        assert eod.hour == 16
        assert eod.minute == 59
        assert eod.second == 59
        assert eod.tzinfo is not None, "Should be timezone-aware"

    def test_compute_end_of_day_utc(self):
        """UTC: end of 2026-07-26 = 2026-07-26T23:59:59Z"""
        d = date(2026, 7, 26)
        eod = compute_end_of_day(d, "UTC")
        assert eod.day == 26
        assert eod.hour == 23

    def test_compute_end_of_day_utc_plus_14(self):
        """UTC+14 (earliest timezone): end of day rolls back to same day UTC"""
        d = date(2026, 7, 26)
        eod = compute_end_of_day(d, "Pacific/Kiritimati")  # UTC+14
        assert eod.day == 26  # 23:59 UTC+14 = 09:59 UTC
        assert eod.hour == 9
        assert eod.minute == 59


# ===========================================================================
# 2. CANDIDATE TASK FILTERING TESTS
# ===========================================================================


class TestGetCandidateTasks:
    def test_returns_tasks_created_before_end_of_d(self, session: Session, user_id: str):
        """Task created on D should be a candidate."""
        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        task = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            title="Before snapshot",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 1
        assert candidates[0]["id"] == task.id

    def test_excludes_tasks_created_after_end_of_d(self, session: Session, user_id: str):
        """Task created on D+1 should NOT be a candidate for D snapshot."""
        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 16, 0, 0, 0, tzinfo=UTC),
            title="After snapshot",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 0

    def test_includes_task_completed_after_end_of_d(self, session: Session, user_id: str):
        """Task completed on D+1 should still be a candidate (was open at end of D)."""
        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        task = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC),  # Completed AFTER end_of_D
            title="Completed after D",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 1
        assert candidates[0]["id"] == task.id

    def test_excludes_task_completed_before_end_of_d(self, session: Session, user_id: str):
        """Task completed before end_of_D should NOT be a candidate."""
        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC),  # Completed BEFORE end_of_D
            title="Completed before D",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 0

    def test_excludes_soft_deleted_tasks(self, session: Session, user_id: str):
        """Soft-deleted task should NOT be a candidate."""
        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            deleted_at=datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC),
            title="Deleted before D",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 0

    def test_excludes_tasks_from_other_users(self, session: Session, user_id: str):
        """Tasks from other users should not appear."""
        from src.db.models import new_id

        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        other_uid = new_id()
        other_user = User(
            id=other_uid,
            email="other@example.com",
            password_hash="fake",
            name="Other",
            timezone="UTC",
        )
        session.add(other_user)
        session.flush()

        _make_task(
            session, other_uid,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            title="Other user's task",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 0

    def test_includes_assigned_plan_date(self, session: Session, user_id: str):
        """Candidate tasks should include assigned_plan_date from LEFT JOIN."""
        snapshot_d = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot_d, "Asia/Saigon")

        plan = _make_plan(session, user_id, "2026-07-14")
        task = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=plan.id,
            title="With plan",
        )

        candidates = _get_candidate_tasks(session, user_id, end_of_d)
        assert len(candidates) == 1
        assert candidates[0]["assigned_plan_date"] == "2026-07-14"
        assert candidates[0]["daily_plan_id"] == plan.id


# ===========================================================================
# 3. LABEL ASSIGNMENT TESTS
# ===========================================================================


class TestGetPlanForDate:
    def test_returns_plan_id_for_confirmed_plan(self, session: Session, user_id: str):
        plan = _make_plan(session, user_id, "2026-07-11", status="confirmed")
        result = _get_plan_for_date(session, user_id, date(2026, 7, 11))
        assert result is not None
        assert result[0] == plan.id
        assert result[1] == "confirmed"

    def test_returns_none_for_draft_plan(self, session: Session, user_id: str):
        _make_plan(session, user_id, "2026-07-11", status="draft")
        result = _get_plan_for_date(session, user_id, date(2026, 7, 11))
        assert result is None

    def test_returns_none_when_no_plan(self, session: Session, user_id: str):
        result = _get_plan_for_date(session, user_id, date(2026, 7, 11))
        assert result is None


class TestGetLabel:
    def test_label_1_when_task_daily_plan_id_matches(self, session: Session, user_id: str):
        """Task assigned to D+1's plan should get label=1."""
        plan = _make_plan(session, user_id, "2026-07-11", status="confirmed")
        task = _make_task(session, user_id, daily_plan_id=plan.id)

        label = _get_label(
            session, task.id, plan.id,
            pre_fetched_task_plan_id=task.daily_plan_id,
        )
        assert label == 1

    def test_label_0_when_task_in_different_plan(self, session: Session, user_id: str):
        """Task assigned to a different plan should get label=0."""
        plan = _make_plan(session, user_id, "2026-07-11", status="confirmed")
        other_plan = _make_plan(session, user_id, "2026-07-10", status="confirmed")
        task = _make_task(session, user_id, daily_plan_id=other_plan.id)

        label = _get_label(
            session, task.id, plan.id,
            pre_fetched_task_plan_id=task.daily_plan_id,
        )
        assert label == 0

    def test_label_0_when_task_has_no_plan(self, session: Session, user_id: str):
        """Task with no daily_plan_id should get label=0."""
        plan = _make_plan(session, user_id, "2026-07-11", status="confirmed")
        task = _make_task(session, user_id, daily_plan_id=None)

        label = _get_label(
            session, task.id, plan.id,
            pre_fetched_task_plan_id=None,
        )
        assert label == 0

    def test_label_1_via_schedule_item(self, session: Session, user_id: str):
        """Task linked to plan via ScheduleItem (not daily_plan_id) should get label=1."""
        plan = _make_plan(session, user_id, "2026-07-11", status="confirmed")
        task = _make_task(session, user_id, daily_plan_id=None)

        _make_schedule_item(session, plan.id, task.id)

        label = _get_label(
            session, task.id, plan.id,
            pre_fetched_task_plan_id=task.daily_plan_id,
        )
        assert label == 1


# ===========================================================================
# 4. FEATURE EXTRACTION TESTS
# ===========================================================================


class TestComputeTaskFeatures:
    def test_basic_features(self):
        snapshot = date(2026, 7, 15)
        eod = compute_end_of_day(snapshot, "UTC")
        task = {
            "created_at": datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            "deadline": "2026-07-20",
            "estimated_duration": 45,
            "priority": "high",
            "task_type": "scheduled",
            "tags": ["work", "urgent"],
            "description": "Do the thing",
        }
        feats = _compute_task_features(task, snapshot, eod)

        assert feats["task_age_days"] == 5  # July 15 - July 10
        assert feats["has_deadline"] is True
        assert feats["is_overdue"] is False  # deadline July 20 > July 15
        assert feats["deadline_relative_days"] == 5  # July 20 - July 15
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
        snapshot = date(2026, 7, 15)
        eod = compute_end_of_day(snapshot, "UTC")
        task = {
            "created_at": datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            "deadline": "2026-07-14",
            "estimated_duration": None,
            "priority": None,
            "task_type": "flexible",
            "tags": [],
            "description": None,
        }
        feats = _compute_task_features(task, snapshot, eod)

        assert feats["is_overdue"] is True
        assert feats["deadline_relative_days"] == -1  # July 14 - July 15
        assert feats["has_estimated_duration"] is False
        assert feats["estimated_duration"] == 30  # default
        assert feats["priority_normal"] is True  # default
        assert feats["task_type_scheduled"] is False
        assert feats["task_type_flexible"] is True
        assert feats["num_tags"] == 0
        assert feats["has_description"] is False
        assert feats["description_length"] == 0

    def test_no_deadline(self):
        snapshot = date(2026, 7, 15)
        eod = compute_end_of_day(snapshot, "UTC")
        task = {
            "created_at": datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            "deadline": None,
            "estimated_duration": None,
            "priority": None,
            "task_type": "scheduled",
            "tags": [],
            "description": None,
        }
        feats = _compute_task_features(task, snapshot, eod)
        assert feats["has_deadline"] is False
        assert feats["is_overdue"] is False
        assert feats["deadline_relative_days"] == MAX_SAFE_INT


class TestGetTemporalFeatures:
    def test_monday_not_day_off(self):
        feats = _get_temporal_features(date(2026, 7, 27), False)
        assert feats["target_day_of_week"] == 0  # Monday
        assert feats["target_is_monday"] is True
        assert feats["target_is_weekend"] is False
        assert feats["target_is_day_off"] is False
        assert feats["target_weekday_name"] == "Monday"

    def test_sunday_is_day_off(self):
        feats = _get_temporal_features(date(2026, 8, 2), True)
        assert feats["target_day_of_week"] == 6  # Sunday
        assert feats["target_is_weekend"] is True
        assert feats["target_is_day_off"] is True
        assert feats["target_weekday_name"] == "Sunday"

    def test_weekday_names_list(self):
        assert WEEKDAY_NAMES[0] == "Monday"
        assert WEEKDAY_NAMES[6] == "Sunday"
        assert len(WEEKDAY_NAMES) == 7


class TestBatchReconstructStatuses:
    def test_no_events_returns_todo(self, session: Session, user_id: str):
        task = _make_task(session, user_id)
        result = _batch_reconstruct_statuses(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id] == "todo"

    def test_task_completed_event(self, session: Session, user_id: str):
        task = _make_task(session, user_id, created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC))
        session.add(ActivityEvent(
            id="evt-001",
            user_id=user_id,
            event_type="task_completed",
            entity_type="task",
            entity_id=task.id,
            source="manual",
            payload={},
            occurred_at=datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC),
        ))
        session.flush()

        result = _batch_reconstruct_statuses(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id] == "completed"

    def test_task_skipped_event(self, session: Session, user_id: str):
        task = _make_task(session, user_id, created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC))
        session.add(ActivityEvent(
            id="evt-002",
            user_id=user_id,
            event_type="task_skipped",
            entity_type="task",
            entity_id=task.id,
            source="manual",
            payload={},
            occurred_at=datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC),
        ))
        session.flush()

        result = _batch_reconstruct_statuses(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id] == "skipped"

    def test_event_after_end_of_d_is_ignored(self, session: Session, user_id: str):
        task = _make_task(session, user_id, created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC))
        # Event AFTER end_of_d
        session.add(ActivityEvent(
            id="evt-003",
            user_id=user_id,
            event_type="task_completed",
            entity_type="task",
            entity_id=task.id,
            source="manual",
            payload={},
            occurred_at=datetime(2026, 7, 25, 10, 0, 0, tzinfo=UTC),
        ))
        session.flush()

        result = _batch_reconstruct_statuses(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id] == "todo"  # event ignored


class TestBatchGetEventCounts:
    def test_no_events_returns_defaults(self, session: Session, user_id: str):
        task = _make_task(session, user_id)
        result = _batch_get_event_counts(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id]["completion_count_7d"] == 0
        assert result[task.id]["days_since_last_completion"] == MAX_SAFE_INT

    def test_counts_events_in_window(self, session: Session, user_id: str):
        task = _make_task(session, user_id, created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC))
        # Event within lookback window (7 days before July 20 = after July 13)
        session.add(ActivityEvent(
            id="evt-004",
            user_id=user_id,
            event_type="task_completed",
            entity_type="task",
            entity_id=task.id,
            source="manual",
            payload={},
            occurred_at=datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC),
        ))
        session.flush()

        result = _batch_get_event_counts(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id]["completion_count_7d"] == 1

    def test_excludes_events_before_window(self, session: Session, user_id: str):
        """Events before the 7-day lookback window should be excluded."""
        task = _make_task(session, user_id, created_at=datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC))
        # Event 15 days BEFORE end_of_d (before 7-day lookback)
        session.add(ActivityEvent(
            id="evt-005",
            user_id=user_id,
            event_type="task_completed",
            entity_type="task",
            entity_id=task.id,
            source="manual",
            payload={},
            occurred_at=datetime(2026, 7, 5, 10, 0, 0, tzinfo=UTC),
        ))
        session.flush()

        result = _batch_get_event_counts(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        assert result[task.id]["completion_count_7d"] == 0  # excluded

    def test_days_since_last_completion(self, session: Session, user_id: str):
        """Verify days_since_last_completion is calculated correctly."""
        task = _make_task(session, user_id, created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC))
        session.add(ActivityEvent(
            id="evt-006",
            user_id=user_id,
            event_type="task_completed",
            entity_type="task",
            entity_id=task.id,
            source="manual",
            payload={},
            occurred_at=datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC),
        ))
        session.flush()

        result = _batch_get_event_counts(
            session, user_id, [task.id],
            end_of_d=datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC),
        )
        # 4 days between July 15 10:00 and July 20 00:00 (floor division)
        assert result[task.id]["days_since_last_completion"] == 4


# ===========================================================================
# 5. USER CONTEXT FEATURES TESTS
# ===========================================================================


class TestGetUserContextFeatures:
    def test_basic_features(self, session: Session, user_id: str, preferences):
        """Basic user context features with one open task."""
        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            title="Task 1",
        )
        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 12, 0, 0, 0, tzinfo=UTC),
            task_type="flexible",
            title="Task 2",
        )
        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC),  # completed before snapshot
            title="Task 3 (completed)",
        )
        session.flush()

        snapshot = date(2026, 7, 20)
        target = date(2026, 7, 21)
        end_of_d = compute_end_of_day(snapshot, "Asia/Saigon")

        feats = _get_user_context_features(
            session, user_id, end_of_d, "Asia/Saigon", target, snapshot,
        )

        # Only 2 open tasks (task 3 completed before end_of_D)
        assert feats["user_total_open_tasks"] == 2
        assert feats["user_scheduled_count"] == 1  # only task 1 is scheduled
        assert feats["user_flexible_count"] == 1  # only task 2 is flexible
        assert feats["user_completed_count_7d"] >= 0
        assert feats["days_since_last_plan"] == MAX_SAFE_INT  # no plans before target

    def test_with_recent_plan(self, session: Session, user_id: str, preferences):
        """days_since_last_plan should be computed from recent plan."""
        # Create a plan on July 18
        _make_plan(session, user_id, "2026-07-18", status="confirmed")

        snapshot = date(2026, 7, 20)
        target = date(2026, 7, 21)
        end_of_d = compute_end_of_day(snapshot, "Asia/Saigon")

        feats = _get_user_context_features(
            session, user_id, end_of_d, "Asia/Saigon", target, snapshot,
        )
        # July 20 - July 18 = 2 days
        assert feats["days_since_last_plan"] == 2


class TestGetPreferences:
    def test_returns_preferences(self, session: Session, user_id: str, preferences):
        """Get preferences should return the stored values."""
        prefs = _get_preferences(session, user_id)
        assert prefs["timezone"] == "Asia/Saigon"
        assert prefs["work_start"] == "09:00"
        assert prefs["work_end"] == "17:00"
        assert prefs["lunch_start"] == "12:00"
        assert prefs["lunch_end"] == "13:00"
        assert prefs["day_offs"] == ["Saturday", "Sunday"]

    def test_returns_defaults_when_no_preferences(self, session: Session, user_id: str):
        """No preferences should return sensible defaults."""
        prefs = _get_preferences(session, user_id)
        assert prefs["timezone"] == "Asia/Saigon"
        assert prefs["work_start"] == "09:00"  # defaults from query
        assert prefs["day_offs"] == []


# ===========================================================================
# 6. INTEGRATION TESTS
# ===========================================================================


class TestBuildRowsForSnapshot:
    def test_empty_candidates_returns_empty(self, session: Session, user_id: str, preferences):
        """No candidates should produce empty list."""
        prefs = _get_preferences(session, user_id)
        snapshot = date(2026, 7, 15)
        rows = _build_rows_for_snapshot(session, user_id, snapshot, prefs)
        assert rows == []

    def test_basic_snapshot_with_label_1(self, session: Session, user_id: str, preferences):
        """Task from D that is in D+1's plan should have label=1."""
        snapshot = date(2026, 7, 15)
        target = date(2026, 7, 16)

        # Create a plan for D+1
        plan = _make_plan(session, user_id, target.isoformat(), status="confirmed")

        # Create a task on D with daily_plan_id = D+1 plan
        task = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=plan.id,
            title="Task for tomorrow",
        )

        prefs = _get_preferences(session, user_id)
        rows = _build_rows_for_snapshot(session, user_id, snapshot, prefs)

        assert len(rows) == 1
        assert rows[0]["task_id"] == task.id
        assert rows[0]["label"] == 1
        assert rows[0]["snapshot_date"] == "2026-07-15"
        assert rows[0]["target_date"] == "2026-07-16"

    def test_basic_snapshot_with_label_0(self, session: Session, user_id: str, preferences):
        """Task from D that is NOT in D+1's plan should have label=0."""
        snapshot = date(2026, 7, 15)

        # Create a plan for D+1
        target_plan = _make_plan(session, user_id, "2026-07-16", status="confirmed")

        # Create a task on D with NO daily_plan_id
        task = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=None,
            title="Not planned for tomorrow",
        )

        prefs = _get_preferences(session, user_id)
        rows = _build_rows_for_snapshot(session, user_id, snapshot, prefs)

        assert len(rows) == 1
        assert rows[0]["task_id"] == task.id
        assert rows[0]["label"] == 0

    def test_multiple_tasks_correct_labels(self, session: Session, user_id: str, preferences):
        """Verify correct labels for tasks: some in D+1 plan, some not."""
        snapshot = date(2026, 7, 15)
        plan = _make_plan(session, user_id, "2026-07-16", status="confirmed")

        # Task 1: in the plan (label=1)
        t1 = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=plan.id,
            title="In plan",
        )
        # Task 2: not in plan (label=0)
        t2 = _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=None,
            title="Not in plan",
        )

        prefs = _get_preferences(session, user_id)
        rows = _build_rows_for_snapshot(session, user_id, snapshot, prefs)

        labels = {r["task_id"]: r["label"] for r in rows}
        assert labels[t1.id] == 1
        assert labels[t2.id] == 0
        assert len(rows) == 2

    def test_five_tasks_two_in_plan_correct_labels(self, session: Session, user_id: str, preferences):
        """5 tasks, 2 with daily_plan_id = D+1 plan, 3 without → labels = [1,1,0,0,0].

        Uses title-based lookup instead of positional order because ORDER BY created_at
        is the same for all tasks (same timestamp), so return order is undefined.
        """
        snapshot = date(2026, 7, 15)
        plan = _make_plan(session, user_id, "2026-07-16", status="confirmed")

        _make_task(session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=plan.id, title="Task A - in plan", deadline="2026-07-16")
        _make_task(session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=plan.id, title="Task B - in plan", deadline="2026-07-17")
        _make_task(session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=None, title="Task C - not in plan", deadline="2026-08-01")
        _make_task(session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=None, title="Task D - not in plan", deadline="2026-08-10")
        _make_task(session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=None, title="Task E - not in plan", deadline="2026-09-01")

        prefs = _get_preferences(session, user_id)
        rows = _build_rows_for_snapshot(session, user_id, snapshot, prefs)

        assert len(rows) == 5
        label_by_title = {r["task_title_hint"]: r["label"] for r in rows}
        expected = {
            "Task A - in plan": 1,
            "Task B - in plan": 1,
            "Task C - not in plan": 0,
            "Task D - not in plan": 0,
            "Task E - not in plan": 0,
        }
        assert label_by_title == expected, f"Expected {expected}, got {label_by_title}"

    def test_snapshot_skips_tasks_from_d_plus_1(self, session: Session, user_id: str, preferences):
        """Tasks created on D+1 should not appear in D's snapshot."""
        snapshot = date(2026, 7, 15)
        end_of_d = compute_end_of_day(snapshot, "Asia/Saigon")

        # Task created on D (should be candidate)
        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
            title="Created on D",
        )
        # Task created on D+1 (should NOT be candidate)
        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 16, 0, 0, 0, tzinfo=UTC),
            title="Created on D+1",
        )

        prefs = _get_preferences(session, user_id)
        rows = _build_rows_for_snapshot(session, user_id, snapshot, prefs)

        assert len(rows) == 1  # Only the D task
        assert rows[0]["task_age_days"] == 1  # 1 day old at snapshot


class TestBuildDataset:
    def test_empty_database(self, session: Session):
        """build_dataset should return empty DataFrame with no users."""
        from_date = date(2026, 7, 10)
        to_date = date(2026, 7, 12)
        df = build_dataset(
            session, from_date, to_date,
            min_history_days=0,
        )
        assert df.empty

    def test_full_pipeline_one_snapshot(self, session: Session, user_id: str, preferences):
        """End-to-end: single snapshot with one task in plan."""
        # Create plan for tomorrow
        target_plan = _make_plan(session, user_id, "2026-07-11", status="confirmed")

        # Create task in the plan
        _make_task(
            session, user_id,
            created_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
            daily_plan_id=target_plan.id,
            title="Planned task",
        )

        from_date = date(2026, 7, 10)
        to_date = date(2026, 7, 10)
        df = build_dataset(
            session, from_date, to_date,
            user_id=user_id,
            min_history_days=0,
        )

        assert not df.empty
        assert len(df) == 1
        assert df.iloc[0]["label"] == 1
        assert df.iloc[0]["snapshot_date"] == "2026-07-10"
        assert df.iloc[0]["target_date"] == "2026-07-11"
        assert "task_title_hint" in df.columns  # present in build_dataset(), dropped in main()

    def test_multiple_days(self, session: Session, user_id: str, preferences):
        """End-to-end: 3 snapshot days, each with different plan status."""
        for day_offset in range(3):
            snap_date = date(2026, 7, 10) + timedelta(days=day_offset)
            target_date = snap_date + timedelta(days=1)

            plan = _make_plan(session, user_id, target_date.isoformat(), status="confirmed")
            _make_task(
                session, user_id,
                created_at=datetime(snap_date.year, snap_date.month, snap_date.day, 0, 0, 0, tzinfo=UTC),
                daily_plan_id=plan.id,
                title=f"Task for {target_date}",
            )

        from_date = date(2026, 7, 10)
        to_date = date(2026, 7, 12)
        df = build_dataset(
            session, from_date, to_date,
            user_id=user_id,
            min_history_days=0,
        )

        # Each snapshot D includes tasks from D and all previous uncompleted days
        # D=10: 1 task, D=11: 2 tasks, D=12: 3 tasks = total 6
        assert len(df) == 6, f"Expected 6 rows, got {len(df)}"
        # Each snapshot has exactly 1 positive label (the task created that day,
        # whose daily_plan_id matches the D+1 target plan)
        assert df["label"].sum() == 3
        assert sorted(df["snapshot_date"].unique()) == ["2026-07-10", "2026-07-11", "2026-07-12"]


# ===========================================================================
# 6. DATE HELPERS
# ===========================================================================


class TestDateFromISO:
    def test_valid_date(self):
        assert date_from_iso("2026-07-26") == date(2026, 7, 26)

    def test_none(self):
        assert date_from_iso(None) is None

    def test_invalid(self):
        assert date_from_iso("not-a-date") is None
