from alembic import op
import sqlalchemy as sa

revision = "0002_outbox_guard"
down_revision = "0001_init_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guard state for circuit breaker (single row per channel)
    op.execute("""
    CREATE TABLE IF NOT EXISTS outbox_guard_state (
      id smallint PRIMARY KEY DEFAULT 1,
      channel varchar(32) NOT NULL,
      state varchar(16) NOT NULL,
      open_until timestamptz NULL,
      last_error text NULL,
      consecutive_failures int NOT NULL DEFAULT 0,
      last_failure_at timestamptz NULL,
      last_success_at timestamptz NULL,
      updated_at timestamptz NOT NULL DEFAULT now(),
      CHECK (id = 1),
      CHECK (state IN ('CLOSED','OPEN','HALF_OPEN'))
    );
    """)

    # Ensure one row for Matrix channel
    op.execute("""
    INSERT INTO outbox_guard_state (id, channel, state)
    VALUES (1, 'matrix', 'CLOSED')
    ON CONFLICT (id) DO NOTHING;
    """)

    # Watchdog support: track when a row entered 'sending'
    op.execute("""
    ALTER TABLE notification_outbox
    ADD COLUMN IF NOT EXISTS sending_started_at timestamptz NULL;
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_outbox_sending_started_at
    ON notification_outbox (sending_started_at);
    """)


def downgrade() -> None:
    # Keep downgrade safe: do not drop columns/tables automatically in MVP
    pass
