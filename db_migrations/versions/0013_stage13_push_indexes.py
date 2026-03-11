"""stage13 push indexes

Revision ID: 0013_stage13_push_indexes
Revises: 0012_stage12_mobile_portal_pwa
Create Date: 2026-03-07
"""

from alembic import op

revision = "0013_stage13_push_indexes"
down_revision = "0012_stage12_mobile_portal_pwa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_subscriptions_user_active ON device_subscriptions (user_id, is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_outbox_channel_status_retry ON notification_outbox (channel, status, next_retry_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_device_subscriptions_user_active")
    op.execute("DROP INDEX IF EXISTS ix_notification_outbox_channel_status_retry")
