"""stage12 fixed mobile portal pwa

Revision ID: 0012_stage12_mobile_portal_pwa
Revises: 0002_outbox_guard
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_stage12_mobile_portal_pwa"
down_revision = "0002_outbox_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    op.create_table(
        "device_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("endpoint", name="uq_device_subscriptions_endpoint"),
    )
    op.create_index("ix_device_subscriptions_user_id", "device_subscriptions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_device_subscriptions_user_id", table_name="device_subscriptions")
    op.drop_table("device_subscriptions")
