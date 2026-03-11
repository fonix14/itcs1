"""stage15 manager task screen"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_stage15_manager_task_screen"
down_revision = "0014_stage14_manager_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_internal_state", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("task_internal_state", sa.Column("closed_by", postgresql.UUID(as_uuid=False), nullable=True))
    op.add_column("task_internal_state", sa.Column("manager_comment", sa.Text(), nullable=True))

    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_task_comments_task_id_created_at", "task_comments", ["task_id", "created_at"], unique=False)


def downgrade():
    op.drop_index("ix_task_comments_task_id_created_at", table_name="task_comments")
    op.drop_table("task_comments")
    op.drop_column("task_internal_state", "manager_comment")
    op.drop_column("task_internal_state", "closed_by")
    op.drop_column("task_internal_state", "closed_at")
