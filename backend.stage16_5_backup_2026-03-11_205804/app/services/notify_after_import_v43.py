from __future__ import annotations

from typing import Any, Iterable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


# -----------------------------
# Variant B:
# - digest per manager per upload
# - immediate notify only for NEW tasks
# -----------------------------

DIGEST_TEMPLATE = "manager_digest"
NEW_TASK_TEMPLATE = "manager_task_new"
CHANNEL = "matrix"


async def enqueue_digest_per_manager(db: AsyncSession, upload_id: str) -> int:
    """
    Creates exactly 1 digest per manager for the given upload_id.
    dedupe_key = digest:{upload_id}:{manager_user_id}
    """
    res = await db.execute(text("""
    WITH mgr AS (
      SELECT DISTINCT s.assigned_user_id AS manager_user_id
      FROM stores s
      WHERE s.assigned_user_id IS NOT NULL
    )
    INSERT INTO notification_outbox (
      channel, recipient_address, template, payload, status, attempts, next_retry_at, dedupe_key
    )
    SELECT
      :channel,
      ''::varchar(512) AS recipient_address,  -- notifier may fallback to MATRIX_ROOM_ID / user-room mapping
      :template,
      jsonb_build_object(
        'upload_id', :upload_id,
        'manager_user_id', mgr.manager_user_id,
        'kind', 'digest'
      ) AS payload,
      'queued',
      0,
      now(),
      ('digest:' || :upload_id || ':' || mgr.manager_user_id::text)
    FROM mgr
    ON CONFLICT (dedupe_key) DO NOTHING
    RETURNING 1;
    """), {"channel": CHANNEL, "template": DIGEST_TEMPLATE, "upload_id": upload_id})
    return len(res.fetchall())


async def enqueue_new_tasks(db: AsyncSession, upload_id: str) -> int:
    """
    Enqueues notifications only for tasks that are NEW in this upload.
    Assumption: task_events contains created events linked to upload_id OR tasks has created_at within this import.
    If you don't have task_events for NEW, switch to a staging diff method.
    """

    # Option A (recommended): task_events has event_type='CREATED' with upload_id
    res = await db.execute(text("""
    INSERT INTO notification_outbox (
      channel, recipient_address, template, payload, status, attempts, next_retry_at, dedupe_key
    )
    SELECT
      :channel,
      ''::varchar(512) AS recipient_address,
      :template,
      jsonb_build_object(
        'upload_id', :upload_id,
        'task_id', e.task_id,
        'manager_user_id', s.assigned_user_id,
        'kind', 'new_task'
      ) AS payload,
      'queued',
      0,
      now(),
      ('newtask:' || e.task_id::text || ':' || s.assigned_user_id::text)
    FROM task_events e
    JOIN tasks t ON t.id = e.task_id
    JOIN stores s ON s.id = t.store_id
    WHERE e.upload_id = :upload_id
      AND e.event_type = 'CREATED'
      AND s.assigned_user_id IS NOT NULL
    ON CONFLICT (dedupe_key) DO NOTHING
    RETURNING 1;
    """), {"channel": CHANNEL, "template": NEW_TASK_TEMPLATE, "upload_id": upload_id})

    return len(res.fetchall())


async def notify_after_import_variant_b(db: AsyncSession, upload_id: str) -> dict[str, Any]:
    """
    Call this once after successful import commit.
    """
    dig = await enqueue_digest_per_manager(db, upload_id)
    newc = await enqueue_new_tasks(db, upload_id)
    return {
      "outbox_digest_enqueued": dig,
      "outbox_new_tasks_enqueued": newc,
      "mode": "B",
    }
