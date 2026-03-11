create table if not exists task_attachments (
    id bigserial primary key,
    task_id bigint not null references tasks(id) on delete cascade,
    file_name text not null,
    content_type text not null,
    object_key text not null unique,
    file_size bigint,
    uploaded_by uuid null references users(id),
    created_at timestamptz not null default now()
);

create index if not exists ix_task_attachments_task_id on task_attachments(task_id);
create index if not exists ix_task_attachments_created_at on task_attachments(created_at desc);
