from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


def new_id() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Saigon", nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)

    tasks: Mapped[list["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    daily_plans: Mapped[list["DailyPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped["UserPreference | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    schedule_preferences: Mapped["UserSchedulePreference | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    user: Mapped["User"] = relationship(back_populates="preferences")


class UserSchedulePreference(Base, TimestampMixin):
    __tablename__ = "user_schedule_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    work_start_time: Mapped[str] = mapped_column(String(5), default="09:00", nullable=False)
    work_end_time: Mapped[str] = mapped_column(String(5), default="17:00", nullable=False)
    lunch_start_time: Mapped[str] = mapped_column(String(5), default="12:00", nullable=False)
    lunch_end_time: Mapped[str] = mapped_column(String(5), default="13:00", nullable=False)
    day_offs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    focus_hours: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    user: Mapped["User"] = relationship(back_populates="schedule_preferences")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DailyPlan(Base, TimestampMixin):
    __tablename__ = "daily_plans"
    __table_args__ = (UniqueConstraint("user_id", "plan_date", name="uq_daily_plans_user_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    plan_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("context_snapshots.id"), nullable=True)

    user: Mapped["User"] = relationship(back_populates="daily_plans")
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="daily_plan", cascade="all, delete-orphan")
    suggestions: Mapped[list["AISuggestion"]] = relationship(back_populates="daily_plan", cascade="all, delete-orphan")


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    daily_plan_id: Mapped[str] = mapped_column(ForeignKey("daily_plans.id"), index=True, nullable=False)
    schedule_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(50), default="day", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

    daily_plan: Mapped["DailyPlan"] = relationship(back_populates="schedules")
    items: Mapped[list["ScheduleItem"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")


class Task(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    daily_plan_id: Mapped[str | None] = mapped_column(ForeignKey("daily_plans.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    task_type: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="todo", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tasks")


class ScheduleItem(Base, TimestampMixin):
    __tablename__ = "schedule_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("schedules.id"), index=True, nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    start_time: Mapped[str] = mapped_column(String(25), nullable=False)
    end_time: Mapped[str] = mapped_column(String(25), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="planned", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

    schedule: Mapped["Schedule"] = relationship(back_populates="items")


class AISuggestion(Base, TimestampMixin):
    __tablename__ = "ai_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    daily_plan_id: Mapped[str | None] = mapped_column(ForeignKey("daily_plans.id"), nullable=True, index=True)
    context_snapshot_id: Mapped[str] = mapped_column(ForeignKey("context_snapshots.id"), nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    daily_plan: Mapped["DailyPlan"] = relationship(back_populates="suggestions")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ContextSnapshot(Base, TimestampMixin):
    __tablename__ = "context_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class MLPredictionLog(Base, TimestampMixin):
    """Logs ML model predictions for candidate tasks during daily plan generation.

    Each row represents one scored task from one plan generation call.
    The ``outcome`` field is filled asynchronously by reconciling against
    ``ActivityEvent`` (e.g., task_completed → outcome=completed).
    This table is the primary source for monitoring prediction quality,
    feedback signals, and drift detection.
    """

    __tablename__ = "ml_prediction_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("daily_plans.id"), index=True, nullable=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True, nullable=False)
    prediction_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(10), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="completed/skipped/deferred/pending — reconciled via ActivityEvent")
    outcome_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DaySummary(Base, TimestampMixin):
    __tablename__ = "day_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    summary_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    summary_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
