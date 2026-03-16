create extension if not exists pgcrypto;

create table if not exists task_internal_state (
    task_id uuid primary key references tasks(id) on delete cascade,
    internal_status text not null default 'new',
    accepted_at timestamptz null,
    accepted_by uuid null references users(id),
    closed_at timestamptz null,
    closed_by uuid null references users(id),
    manager_comment text null,
    updated_at timestamptz not null default now()
);

create table if not exists task_comments (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references tasks(id) on delete cascade,
    created_by uuid null references users(id),
    comment_text text not null,
    created_at timestamptz not null default now()
);

create table if not exists task_events (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references tasks(id) on delete cascade,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists ix_task_comments_task_id_created_at on task_comments(task_id, created_at desc);
create index if not exists ix_task_events_task_id_created_at on task_events(task_id, created_at desc);
