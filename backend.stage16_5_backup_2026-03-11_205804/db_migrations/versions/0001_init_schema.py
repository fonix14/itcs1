from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # UUID generator
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # -------------------------
    # users
    # -------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('dispatcher','manager')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # -------------------------
    # stores
    # -------------------------
    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("store_no", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("uq_stores_store_no", "stores", ["store_no"], unique=True)
    op.create_index("ix_stores_assigned_user_id", "stores", ["assigned_user_id"], unique=False)

    # -------------------------
    # uploads
    # -------------------------
    op.create_table(
        "uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile", sa.String(100), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("rows_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_valid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_invalid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_ratio", sa.Numeric(6, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_uploads_profile_created_at", "uploads", ["profile", "created_at"], unique=False)

    # -------------------------
    # upload_metrics (baseline / coverage)
    # -------------------------
    op.create_table(
        "upload_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile", sa.String(100), nullable=False),
        sa.Column("coverage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage_baseline", sa.Numeric(12, 3), nullable=True),
        sa.Column("coverage_drop_abs", sa.Numeric(12, 3), nullable=True),
        sa.Column("coverage_drop_rel", sa.Numeric(12, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_upload_metrics_upload_id", "upload_metrics", ["upload_id"], unique=True)
    op.create_index("ix_upload_metrics_profile_created_at", "upload_metrics", ["profile", "created_at"], unique=False)

    # -------------------------
    # import_errors (soft import: invalid rows log)
    # -------------------------
    op.create_table(
        "import_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("row_no", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_import_errors_upload_id", "import_errors", ["upload_id"], unique=False)

    # -------------------------
    # anomalies
    # -------------------------
    op.create_table(
        "anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),  # e.g. STORE_CHANGED, MISSING_MANAGER...
        sa.Column("severity", sa.String(20), nullable=False),  # critical/major/minor
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'open'")),  # open/resolved
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("severity IN ('critical','major','minor')", name="ck_anomalies_severity"),
        sa.CheckConstraint("status IN ('open','resolved')", name="ck_anomalies_status"),
    )
    op.create_index("ix_anomalies_status_severity", "anomalies", ["status", "severity"], unique=False)
    op.create_index("ix_anomalies_last_seen_at", "anomalies", ["last_seen_at"], unique=False)

    # -------------------------
    # tasks (mirror of supplier portal tasks)
    # -------------------------
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("portal_task_id", sa.String(64), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),  # mirror: OPEN/CLOSED/... (string)
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("uq_tasks_portal_task_id", "tasks", ["portal_task_id"], unique=True)
    op.create_index("ix_tasks_store_id", "tasks", ["store_id"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)

    # -------------------------
    # task_events (optional audit)
    # -------------------------
    op.create_table(
        "task_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("data", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_task_events_task_id", "task_events", ["task_id"], unique=False)

    # -------------------------
    # notifications outbox (Stage 4)
    # -------------------------
    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("channel", sa.String(32), nullable=False),  # matrix/email/webpush
        sa.Column("recipient_address", sa.String(512), nullable=False),  # room_id / email / endpoint
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(512), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued','sending','sent','failed','dead')", name="ck_outbox_status"),
    )
    op.create_index("uq_outbox_dedupe", "notification_outbox", ["dedupe_key"], unique=True)
    op.create_index("ix_outbox_status_retry", "notification_outbox", ["status", "next_retry_at"], unique=False)

    op.create_table(
        "notification_worker_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.execute("INSERT INTO notification_worker_state (id) VALUES (1) ON CONFLICT DO NOTHING;")


def downgrade() -> None:
    op.drop_table("notification_worker_state")
    op.drop_index("ix_outbox_status_retry", table_name="notification_outbox")
    op.drop_index("uq_outbox_dedupe", table_name="notification_outbox")
    op.drop_table("notification_outbox")

    op.drop_index("ix_task_events_task_id", table_name="task_events")
    op.drop_table("task_events")

    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_store_id", table_name="tasks")
    op.drop_index("uq_tasks_portal_task_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_anomalies_last_seen_at", table_name="anomalies")
    op.drop_index("ix_anomalies_status_severity", table_name="anomalies")
    op.drop_table("anomalies")

    op.drop_index("ix_import_errors_upload_id", table_name="import_errors")
    op.drop_table("import_errors")

    op.drop_index("ix_upload_metrics_profile_created_at", table_name="upload_metrics")
    op.drop_index("ix_upload_metrics_upload_id", table_name="upload_metrics")
    op.drop_table("upload_metrics")

    op.drop_index("ix_uploads_profile_created_at", table_name="uploads")
    op.drop_table("uploads")

    op.drop_index("ix_stores_assigned_user_id", table_name="stores")
    op.drop_index("uq_stores_store_no", table_name="stores")
    op.drop_table("stores")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
