from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import NotificationOutbox
from app.notifications.outbox import maybe_enqueue_daily_health
from app.notifier.backoff import next_retry
from app.notifier.matrix import MatrixClient
from app.notifier.templates import render_digest_after_upload, render_daily_health
from app.settings import settings


NOTIFIER_ACTOR_USER_ID = os.getenv("NOTIFIER_ACTOR_USER_ID", "00000000-0000-0000-0000-000000000000")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _update_worker_state(db: AsyncSession, *, last_tick_at: datetime | None = None, last_sent_at: datetime | None = None, last_error: str | None = None) -> None:
    await db.execute(
        text(
            """
            UPDATE notification_worker_state
            SET last_tick_at = COALESCE(:last_tick_at, last_tick_at),
                last_sent_at = COALESCE(:last_sent_at, last_sent_at),
                last_error = :last_error
            WHERE id = 1
            """
        ),
        {"last_tick_at": last_tick_at, "last_sent_at": last_sent_at, "last_error": last_error},
    )


async def _lock_batch(db: AsyncSession) -> list[dict]:
    # Lock a batch of queued items
    q = text(
        """
        WITH cte AS (
            SELECT id
            FROM notification_outbox
            WHERE status = 'queued'
              AND next_retry_at <= now()
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT :lim
        )
        UPDATE notification_outbox o
        SET status = 'sending'
        FROM cte
        WHERE o.id = cte.id
        RETURNING o.id, o.channel, o.recipient_address, o.template, o.payload, o.attempts
        """
    )
    res = await db.execute(q, {"lim": settings.notifier_lock_batch_size})
    return [dict(r) for r in res.mappings().all()]


async def _mark_sent(db: AsyncSession, outbox_id: str, now: datetime) -> None:
    await db.execute(
        text(
            """
            UPDATE notification_outbox
            SET status='sent', sent_at=:now, last_error=NULL
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": outbox_id, "now": now},
    )


async def _mark_failed(db: AsyncSession, outbox_id: str, attempts: int, err: str, now: datetime) -> None:
    max_attempts = settings.notifier_max_attempts
    new_attempts = attempts + 1
    if new_attempts >= max_attempts:
        await db.execute(
            text(
                """
                UPDATE notification_outbox
                SET status='dead', attempts=:a, last_error=:e
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": outbox_id, "a": new_attempts, "e": err},
        )
        return

    nr = next_retry(new_attempts, now)
    await db.execute(
        text(
            """
            UPDATE notification_outbox
            SET status='queued', attempts=:a, last_error=:e, next_retry_at=:nr
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": outbox_id, "a": new_attempts, "e": err, "nr": nr},
    )


async def _send_one(item: dict, mx: MatrixClient) -> None:
    outbox_id = str(item["id"])
    channel = item.get("channel")
    template = item.get("template")
    room_id = item.get("recipient_address") or settings.matrix_room_id

    if channel != "matrix":
        raise RuntimeError(f"unsupported_channel:{channel}")

    if not settings.matrix_base_url or not settings.matrix_access_token:
        raise RuntimeError("matrix_not_configured")

    if not room_id:
        raise RuntimeError("matrix_room_id_missing")

    payload = item.get("payload") or {}

    if template == "digest_after_upload":
        body = render_digest_after_upload(payload)
    elif template == "daily_health":
        body = render_daily_health(payload)
    else:
        body = f"ITCS уведомление ({template})\n\n{payload}"

    await mx.send_text(room_id=room_id, txn_id=outbox_id, body=body)


async def run_forever() -> None:
    mx = MatrixClient(settings.matrix_base_url, settings.matrix_access_token)

    while True:
        now = _utc_now()
        try:
            async with db_session(NOTIFIER_ACTOR_USER_ID, "dispatcher") as db:
                await _update_worker_state(db, last_tick_at=now, last_error=None)

                # Daily health generator inside notifier (dedupe_key ensures 1/day)
                if now.hour == int(settings.notifier_daily_health_hour_utc):
                    try:
                        await maybe_enqueue_daily_health(db, now_utc=now)
                    except Exception as e:
                        # Do not crash worker on generator errors
                        await _update_worker_state(db, last_error=f"daily_health_enqueue:{type(e).__name__}:{e}")

                batch = await _lock_batch(db)
                if not batch:
                    await db.commit()
                else:
                    # Commit early so other workers don't wait on locks too long
                    await db.commit()

            # Send outside DB transaction (avoid holding locks)
            for item in batch:
                send_now = _utc_now()
                try:
                    await _send_one(item, mx)
                    async with db_session(NOTIFIER_ACTOR_USER_ID, "dispatcher") as db2:
                        await _mark_sent(db2, str(item["id"]), send_now)
                        await _update_worker_state(db2, last_sent_at=send_now, last_error=None)
                        await db2.commit()
                except Exception as e:
                    err = f"send_failed:{type(e).__name__}:{e}"

                    # Fail-safe for auth errors: mark dead immediately (critical)
                    auth_dead = False
                    try:
                        import httpx

                        if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
                            if e.response.status_code in (401, 403):
                                auth_dead = True
                                err = f"matrix_auth_failed:{e.response.status_code}"
                    except Exception:
                        pass

                    async with db_session(NOTIFIER_ACTOR_USER_ID, "dispatcher") as db3:
                        if auth_dead:
                            await db3.execute(
                                text(
                                    "UPDATE notification_outbox SET status='dead', attempts=attempts+1, last_error=:e WHERE id=CAST(:id AS uuid)"
                                ),
                                {"id": str(item["id"]), "e": err},
                            )
                        else:
                            await _mark_failed(db3, str(item["id"]), int(item.get("attempts") or 0), err, send_now)
                        await _update_worker_state(db3, last_error=err)
                        await db3.commit()

        except Exception as e:
            # hard-loop resilience
            try:
                async with db_session(NOTIFIER_ACTOR_USER_ID, "dispatcher") as db4:
                    await _update_worker_state(db4, last_error=f"worker_exception:{type(e).__name__}:{e}")
                    await db4.commit()
            except Exception:
                pass

        await asyncio.sleep(int(settings.outbox_poll_interval_sec))


if __name__ == "__main__":
    asyncio.run(run_forever())
