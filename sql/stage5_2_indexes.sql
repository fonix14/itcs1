create index if not exists ix_tasks_store_status on tasks(store_id,status);
create index if not exists ix_tasks_sla_due on tasks(sla_due_at);
create index if not exists ix_tasks_last_seen on tasks(last_seen_at);