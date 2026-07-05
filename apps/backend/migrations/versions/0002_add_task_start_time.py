"""add task start time

Revision ID: 0002_add_task_start_time
Revises: 0001_initial_schema
Create Date: 2026-07-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_add_task_start_time"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("start_time", sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "start_time")
