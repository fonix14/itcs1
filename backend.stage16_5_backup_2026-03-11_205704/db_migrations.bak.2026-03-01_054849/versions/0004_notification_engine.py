"""stage4 notification engine (matrix digest + daily health)

Revision ID: 0004_notification_engine
Revises: 0003_notifications

Notes:
- We extend existing notification_outbox (created in 0003) to support Stage 4 outbox semantics.
- We keep legacy columns (kind, user_id) for backward compatibility.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_notification_engine"
down_revision = "0003_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- notification_outbox extensions ----
    op.add_column("notification_outbox", sa.Column("channel", sa.Text(), nullable=False, server_default=sa.text("'matrix'")))
    op.add_column("notification_outbox", sa.Column("recipient_address", sa.Text(), nullable=False, server_default=sa.text("''")))
    op.add_column("notification_outbox", sa.Column("template", sa.Text(), nullable=False, server_default=sa.text("''")))
    op.add_column("notification_outbox", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.add_column("notification_outbox", sa.Column("dedupe_key", sa.Text(), nullable=False, server_default=sa.text("''")))

    # status migration: pending -> queued
    op.execute("UPDATE notification_outbox SET status = 'queued' WHERE status = 'pending';")

    # Make legacy columns nullable (Stage 4 uses room-based recipients)
    op.alter_column("notification_outbox", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("notification_outbox", "kind", existing_type=sa.String(length=80), nullable=True)

    # Backfill template from legacy kind where missing
    op.execute("UPDATE notification_outbox SET template = COALESCE(NULLIF(template,''), kind, '')")

    # Indexes (idempotent-ish)
    op.create_index("ix_notification_outbox_status_retry", "notification_outbox", ["status", "next_retry_at"], unique=False)
    op.create_unique_constraint("uq_notification_outbox_dedupe", "notification_outbox", ["dedupe_key"])

    # ---- worker state ----
    op.create_table(
        "notification_worker_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.execute("INSERT INTO notification_worker_state(id) VALUES (1) ON CONFLICT (id) DO NOTHING;")

    # RLS for worker_state: dispatcher only
    op.execute("ALTER TABLE notification_worker_state ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE notification_worker_state FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY nws_dispatcher_all ON notification_worker_state
        FOR ALL USING (app.is_dispatcher()) WITH CHECK (app.is_dispatcher());
        """
    )


def downgrade() -> None:
    op.drop_table("notification_worker_state")
    op.drop_constraint("uq_notification_outbox_dedupe", "notification_outbox", type_="unique")
    op.drop_index("ix_notification_outbox_status_retry", table_name="notification_outbox")

    op.alter_column("notification_outbox", "kind", nullable=False)
    op.alter_column("notification_outbox", "user_id", nullable=False)

    op.drop_column("notification_outbox", "dedupe_key")
    op.drop_column("notification_outbox", "next_retry_at")
    op.drop_column("notification_outbox", "template")
    op.drop_column("notification_outbox", "recipient_address")
    op.drop_column("notification_outbox", "channel")
