CREATE TABLE IF NOT EXISTS task_comments (
    id uuid PRIMARY KEY,
    task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_user_id uuid NULL REFERENCES users(id) ON DELETE SET NULL,
    author_role text NOT NULL,
    author_name text NOT NULL,
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_comments_task_id_created_at
    ON task_comments(task_id, created_at);
