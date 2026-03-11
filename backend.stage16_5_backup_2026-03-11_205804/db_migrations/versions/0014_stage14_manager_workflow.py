"""stage14 manager workflow tables

Revision ID: 0014_stage14_manager_workflow
Revises: 0002_outbox_guard
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_stage14_manager_workflow"
down_revision = "0002_outbox_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    create table if not exists task_internal_state (
        task_id uuid primary key references tasks(id) on delete cascade,
        internal_status varchar(50) not null default 'new',
        accepted_by uuid null references users(id) on delete set null,
        accepted_at timestamptz null,
        updated_at timestamptz not null default now()
    )
    """)

    op.execute("""
    create table if not exists task_comments (
        id uuid primary key,
        task_id uuid not null references tasks(id) on delete cascade,
        author_user_id uuid null references users(id) on delete set null,
        author_role varchar(50) not null default 'manager',
        comment text not null,
        created_at timestamptz not null default now()
    )
    """)
    op.execute("create index if not exists ix_task_comments_task_id_created_at on task_comments(task_id, created_at desc)")

    op.execute("""
    create table if not exists task_events (
        id uuid primary key,
        task_id uuid not null references tasks(id) on delete cascade,
        event_type varchar(80) not null,
        payload jsonb not null default '{}'::jsonb,
        created_at timestamptz not null default now()
    )
    """)
    op.execute("create index if not exists ix_task_events_task_id_created_at on task_events(task_id, created_at desc)")

    op.execute("""
    create table if not exists task_attachments (
        id uuid primary key,
        task_id uuid not null references tasks(id) on delete cascade,
        file_name varchar(255) not null,
        content_type varchar(120) not null,
        object_key varchar(500) not null,
        file_size integer not null default 0,
        uploaded_by uuid null references users(id) on delete set null,
        created_at timestamptz not null default now()
    )
    """)
    op.execute("create index if not exists ix_task_attachments_task_id_created_at on task_attachments(task_id, created_at desc)")


def downgrade() -> None:
    op.execute("drop table if exists task_attachments")
    op.execute("drop table if exists task_events")
    op.execute("drop table if exists task_comments")
    op.execute("drop table if exists task_internal_state")
