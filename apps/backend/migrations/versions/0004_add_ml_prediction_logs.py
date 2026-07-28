"""add ml_prediction_logs table for Phase 6 monitoring

Revision ID: 0004_add_ml_prediction_logs
Revises: 0003_add_task_type
Create Date: 2026-07-27 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_add_ml_prediction_logs"
down_revision = "0003_add_task_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_prediction_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("daily_plans.id"), nullable=True, index=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False, index=True),
        sa.Column("prediction_score", sa.Float, nullable=False),
        sa.Column("confidence_band", sa.String(10), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=True,
                  comment="completed/skipped/deferred/pending — reconciled via ActivityEvent"),
        sa.Column("outcome_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ml_prediction_logs")
