"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default=sa.text("'Asia/Saigon'")),
        sa.Column("role", sa.String(length=50), nullable=False, server_default=sa.text("'user'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default=sa.text("'en'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", name="uq_user_preferences_user_id"),
    )

    op.create_table(
        "user_schedule_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("work_start_time", sa.String(length=5), nullable=False, server_default=sa.text("'09:00'")),
        sa.Column("work_end_time", sa.String(length=5), nullable=False, server_default=sa.text("'17:00'")),
        sa.Column("lunch_start_time", sa.String(length=5), nullable=False, server_default=sa.text("'12:00'")),
        sa.Column("lunch_end_time", sa.String(length=5), nullable=False, server_default=sa.text("'13:00'")),
        sa.Column("day_offs", sa.JSON(), nullable=False),
        sa.Column("focus_hours", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", name="uq_user_schedule_preferences_user_id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_type", sa.String(length=50), nullable=False),
        sa.Column("context_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_context_snapshots_user_id", "context_snapshots", ["user_id"], unique=False)

    op.create_table(
        "daily_plans",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plan_date", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("source", sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
        sa.UniqueConstraint("user_id", "plan_date", name="uq_daily_plans_user_date"),
    )
    op.create_index("ix_daily_plans_user_id", "daily_plans", ["user_id"], unique=False)
    op.create_index("ix_daily_plans_plan_date", "daily_plans", ["plan_date"], unique=False)
    op.create_index("ix_daily_plans_context_snapshot_id", "daily_plans", ["context_snapshot_id"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("daily_plan_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("deadline", sa.String(length=10), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'todo'")),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["daily_plan_id"], ["daily_plans.id"]),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)
    op.create_index("ix_tasks_daily_plan_id", "tasks", ["daily_plan_id"], unique=False)

    op.create_table(
        "schedules",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("daily_plan_id", sa.String(length=36), nullable=False),
        sa.Column("schedule_date", sa.String(length=10), nullable=False),
        sa.Column("schedule_type", sa.String(length=50), nullable=False, server_default=sa.text("'day'")),
        sa.Column("source", sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["daily_plan_id"], ["daily_plans.id"]),
    )
    op.create_index("ix_schedules_user_id", "schedules", ["user_id"], unique=False)
    op.create_index("ix_schedules_daily_plan_id", "schedules", ["daily_plan_id"], unique=False)
    op.create_index("ix_schedules_schedule_date", "schedules", ["schedule_date"], unique=False)

    op.create_table(
        "schedule_items",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("schedule_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("start_time", sa.String(length=25), nullable=False),
        sa.Column("end_time", sa.String(length=25), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'planned'")),
        sa.Column("source", sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
    )
    op.create_index("ix_schedule_items_schedule_id", "schedule_items", ["schedule_id"], unique=False)
    op.create_index("ix_schedule_items_task_id", "schedule_items", ["task_id"], unique=False)

    op.create_table(
        "ai_suggestions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("daily_plan_id", sa.String(length=36), nullable=True),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("suggestion_type", sa.String(length=50), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["daily_plan_id"], ["daily_plans.id"]),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
    )
    op.create_index("ix_ai_suggestions_user_id", "ai_suggestions", ["user_id"], unique=False)
    op.create_index("ix_ai_suggestions_daily_plan_id", "ai_suggestions", ["daily_plan_id"], unique=False)
    op.create_index("ix_ai_suggestions_context_snapshot_id", "ai_suggestions", ["context_snapshot_id"], unique=False)

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"], unique=False)

    op.create_table(
        "activity_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_events_user_id", "activity_events", ["user_id"], unique=False)
    op.create_index("ix_activity_events_event_type", "activity_events", ["event_type"], unique=False)

    op.create_table(
        "day_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("summary_date", sa.String(length=10), nullable=False),
        sa.Column("summary_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_day_summaries_user_id", "day_summaries", ["user_id"], unique=False)
    op.create_index("ix_day_summaries_summary_date", "day_summaries", ["summary_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_day_summaries_summary_date", table_name="day_summaries")
    op.drop_index("ix_day_summaries_user_id", table_name="day_summaries")
    op.drop_table("day_summaries")

    op.drop_index("ix_activity_events_event_type", table_name="activity_events")
    op.drop_index("ix_activity_events_user_id", table_name="activity_events")
    op.drop_table("activity_events")

    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")

    op.drop_index("ix_ai_suggestions_context_snapshot_id", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_daily_plan_id", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_user_id", table_name="ai_suggestions")
    op.drop_table("ai_suggestions")

    op.drop_index("ix_schedule_items_task_id", table_name="schedule_items")
    op.drop_index("ix_schedule_items_schedule_id", table_name="schedule_items")
    op.drop_table("schedule_items")

    op.drop_index("ix_schedules_schedule_date", table_name="schedules")
    op.drop_index("ix_schedules_daily_plan_id", table_name="schedules")
    op.drop_index("ix_schedules_user_id", table_name="schedules")
    op.drop_table("schedules")

    op.drop_index("ix_tasks_daily_plan_id", table_name="tasks")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_daily_plans_context_snapshot_id", table_name="daily_plans")
    op.drop_index("ix_daily_plans_plan_date", table_name="daily_plans")
    op.drop_index("ix_daily_plans_user_id", table_name="daily_plans")
    op.drop_table("daily_plans")

    op.drop_index("ix_context_snapshots_user_id", table_name="context_snapshots")
    op.drop_table("context_snapshots")

    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_constraint("uq_refresh_tokens_token_hash", "refresh_tokens", type_="unique")
    op.drop_table("refresh_tokens")

    op.drop_constraint("uq_user_schedule_preferences_user_id", "user_schedule_preferences", type_="unique")
    op.drop_table("user_schedule_preferences")

    op.drop_constraint("uq_user_preferences_user_id", "user_preferences", type_="unique")
    op.drop_table("user_preferences")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_table("users")
