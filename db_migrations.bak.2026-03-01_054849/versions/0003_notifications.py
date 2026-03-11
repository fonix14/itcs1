"""stage2.5 notifications (device_subscriptions, notification_outbox, task_internal_state, health_state)

Revision ID: 0003_notifications
Revises: 0002_stage2_import
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_notifications"
down_revision = "0002_stage2_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "task_internal_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False, unique=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_comment", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "device_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_status_created", "notification_outbox", ["status", "created_at"])

    op.create_table(
        "health_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_trust_level", sa.String(16), nullable=False, server_default=sa.text("'GREEN'")),
        sa.Column("last_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_notified_trust_level", sa.String(16), nullable=True),
        sa.Column("last_daily_reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute("INSERT INTO health_state(id) VALUES (1) ON CONFLICT (id) DO NOTHING;")

    for t in ["task_internal_state", "device_subscriptions", "notification_outbox", "health_state"]:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")

    op.execute("""
    CREATE POLICY tis_dispatcher_all ON task_internal_state
    FOR ALL USING (app.is_dispatcher()) WITH CHECK (app.is_dispatcher());

    CREATE POLICY tis_manager_rw ON task_internal_state
    FOR ALL USING (
        task_id IN (
            SELECT t.id FROM tasks t
            JOIN stores s ON s.id = t.store_id
            WHERE s.assigned_user_id = app.actor_user_id()
        )
    ) WITH CHECK (
        task_id IN (
            SELECT t.id FROM tasks t
            JOIN stores s ON s.id = t.store_id
            WHERE s.assigned_user_id = app.actor_user_id()
        )
    );

    CREATE POLICY ds_dispatcher_all ON device_subscriptions
    FOR ALL USING (app.is_dispatcher()) WITH CHECK (app.is_dispatcher());

    CREATE POLICY ds_owner_rw ON device_subscriptions
    FOR ALL USING (user_id = app.actor_user_id()) WITH CHECK (user_id = app.actor_user_id());

    CREATE POLICY outbox_dispatcher_all ON notification_outbox
    FOR ALL USING (app.is_dispatcher()) WITH CHECK (app.is_dispatcher());

    CREATE POLICY outbox_owner_read ON notification_outbox
    FOR SELECT USING (user_id = app.actor_user_id());

    CREATE POLICY health_dispatcher_all ON health_state
    FOR ALL USING (app.is_dispatcher()) WITH CHECK (app.is_dispatcher());
    """)


def downgrade() -> None:
    op.drop_table("health_state")
    op.drop_index("ix_outbox_status_created", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_table("device_subscriptions")
    op.drop_table("task_internal_state")
