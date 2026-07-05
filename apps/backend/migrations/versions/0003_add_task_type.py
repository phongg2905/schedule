"""add task_type to tasks

Revision ID: 0003_add_task_type
Revises: 0002_add_task_start_time
Create Date: 2026-07-05 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_task_type"
down_revision = "0002_add_task_start_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("task_type", sa.String(length=20), server_default="scheduled", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("tasks", "task_type")
