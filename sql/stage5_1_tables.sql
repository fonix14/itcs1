CREATE TABLE IF NOT EXISTS task_internal_state (
    task_id uuid PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
    planned_visit_at timestamptz,
    ack_at timestamptz,
    ack_by uuid,
    qc_checked_at timestamptz,
    qc_checked_by uuid,
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_comments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id) ON DELETE CASCADE,
    author_user_id uuid,
    body text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_activity (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id) ON DELETE CASCADE,
    actor_user_id uuid,
    event_type varchar(64),
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);