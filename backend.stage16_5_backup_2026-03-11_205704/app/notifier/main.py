from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Tuple, List

import asyncpg
import httpx
import aiosmtplib
from email.message import EmailMessage
from pywebpush import webpush, WebPushException

from app.notifier.templates_manager import render_manager_task_message
from app.notifier.templates_push import render_push_payload

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notifier")

DATABASE_URL = os.getenv("DATABASE_URL", "")
DSN = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgres://")

MATRIX_BASE_URL = os.getenv("MATRIX_BASE_URL", "").rstrip("/")
MATRIX_ACCESS_TOKEN = os.getenv("MATRIX_ACCESS_TOKEN", "")
DEFAULT_MATRIX_ROOM_ID = os.getenv("MATRIX_ROOM_ID", "")

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "itcs@example.com")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() in ("1", "true", "yes")

POLL_INTERVAL_SEC = int(os.getenv("OUTBOX_POLL_INTERVAL_SEC", "10"))
BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", "20"))
MAX_ATTEMPTS = int(os.getenv("OUTBOX_MAX_ATTEMPTS", "10"))
BACKOFF_BASE_SEC = int(os.getenv("OUTBOX_BACKOFF_BASE_SEC", "10"))
BACKOFF_MAX_SEC = int(os.getenv("OUTBOX_BACKOFF_MAX_SEC", "1800"))
HTTP_TIMEOUT = float(os.getenv("OUTBOX_HTTP_TIMEOUT", "20"))
SENDING_STUCK_MINUTES = int(os.getenv("OUTBOX_SENDING_STUCK_MINUTES", "1"))


def _compute_backoff(attempts: int) -> int:
    sec = BACKOFF_BASE_SEC * (2 ** max(0, attempts))
    return int(min(BACKOFF_MAX_SEC, sec))


def _pretty_json(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(payload)


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def _jsonb_to_dict(v: Any) -> Dict[str, Any]:
    try:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            vv = v.strip()
            if not vv:
                return {}
            obj = json.loads(vv)
            return obj if isinstance(obj, dict) else {}
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


@dataclass
class OutboxRow:
    id: str
    channel: str
    recipient_address: str
    template: str
    payload: Dict[str, Any]
    attempts: int


async def send_matrix_message(room_id: str, text: str) -> None:
    if not MATRIX_BASE_URL or not MATRIX_ACCESS_TOKEN:
        raise RuntimeError("Matrix env not configured")
    txn_id = str(uuid.uuid4())
    url = f"{MATRIX_BASE_URL}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
    body = {"msgtype": "m.text", "body": text, "format": "org.matrix.custom.html", "formatted_body": "<pre>" + _escape_html(text) + "</pre>"}
    headers = {"Authorization": f"Bearer {MATRIX_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.put(url, json=body, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"Matrix send failed: {r.status_code} {r.text[:500]}")


async def send_email_message(to_email: str, subject: str, body: str) -> None:
    if not SMTP_HOST:
        raise RuntimeError("SMTP env not configured")
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    client = aiosmtplib.SMTP(hostname=SMTP_HOST, port=SMTP_PORT, start_tls=SMTP_TLS)
    await client.connect()
    try:
        if SMTP_USER:
            await client.login(SMTP_USER, SMTP_PASS)
        await client.send_message(msg)
    finally:
        await client.quit()


async def _load_active_subscriptions(conn: asyncpg.Connection, manager_user_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        select endpoint, p256dh, auth
        from device_subscriptions
        where user_id = $1::uuid and is_active = true
        """,
        manager_user_id,
    )
    return [dict(r) for r in rows]


async def _load_user_email(conn: asyncpg.Connection, manager_user_id: str) -> str | None:
    row = await conn.fetchrow("select email from users where id = $1::uuid", manager_user_id)
    return row["email"] if row and row.get("email") else None


async def send_webpush_many(conn: asyncpg.Connection, manager_user_id: str, notification: Dict[str, Any]) -> None:
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        raise RuntimeError("VAPID not configured")
    subs = await _load_active_subscriptions(conn, manager_user_id)
    if not subs:
        raise RuntimeError("No active device subscriptions")
    data = json.dumps(notification, ensure_ascii=False).encode("utf-8")
    success = 0
    last_error = None
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}},
                data=data,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_SUBJECT},
            )
            success += 1
        except WebPushException as e:
            last_error = str(e)
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                await conn.execute("update device_subscriptions set is_active=false where endpoint=$1", s["endpoint"])
        except Exception as e:
            last_error = str(e)
    if success <= 0:
        raise RuntimeError(last_error or "webpush_failed")


async def _requeue_stuck_sending(conn: asyncpg.Connection) -> None:
    await conn.execute(
        f"""
        UPDATE notification_outbox
        SET status='queued',
            next_retry_at=now(),
            last_error = COALESCE(last_error,'') || E'\n[auto] stuck in sending > {SENDING_STUCK_MINUTES}m, requeued'
        WHERE status='sending'
          AND created_at < now() - interval '{SENDING_STUCK_MINUTES} minutes'
        """
    )


async def _fetch_and_lock_batch(conn: asyncpg.Connection) -> list[OutboxRow]:
    await _requeue_stuck_sending(conn)
    rows = await conn.fetch(
        """
        WITH picked AS (
          SELECT id
          FROM notification_outbox
          WHERE status = 'queued'
            AND next_retry_at <= now()
          ORDER BY created_at
          LIMIT $1
          FOR UPDATE SKIP LOCKED
        )
        UPDATE notification_outbox o
        SET status='sending'
        FROM picked
        WHERE o.id = picked.id
        RETURNING o.id::text, o.channel, o.recipient_address, o.template, o.payload, o.attempts
        """,
        BATCH_SIZE,
    )
    return [OutboxRow(id=r["id"], channel=r["channel"], recipient_address=r["recipient_address"], template=r["template"], payload=_jsonb_to_dict(r["payload"]), attempts=int(r["attempts"] or 0)) for r in rows]


async def _mark_sent(conn: asyncpg.Connection, row_id: str) -> None:
    await conn.execute("update notification_outbox set status='sent', sent_at=now(), last_error=NULL where id=$1", row_id)


async def _mark_failed(conn: asyncpg.Connection, row_id: str, attempts: int, err: str) -> None:
    if attempts >= MAX_ATTEMPTS:
        await conn.execute("update notification_outbox set status='dead', attempts=$2, last_error=$3, next_retry_at=now() where id=$1", row_id, attempts, str(err)[:4000])
        return
    backoff = _compute_backoff(attempts)
    await conn.execute("update notification_outbox set status='queued', attempts=$2, last_error=$3, next_retry_at=now() + ($4 || ' seconds')::interval where id=$1", row_id, attempts, str(err)[:4000], backoff)


def _payload_tasks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    tasks = payload.get("tasks")
    return [t for t in tasks if isinstance(t, dict)] if isinstance(tasks, list) else []


async def _process_message(pool: asyncpg.Pool, msg: OutboxRow) -> None:
    async with pool.acquire() as conn:
        if msg.channel == "matrix":
            room_id = msg.recipient_address or DEFAULT_MATRIX_ROOM_ID
            if msg.template == "manager_digest" or msg.payload.get("kind") == "manager_digest":
                tasks = _payload_tasks(msg.payload)
                if not tasks:
                    await send_matrix_message(room_id, msg.payload.get("text") or "⚠️ manager_digest: пустой payload")
                else:
                    for t in tasks:
                        await send_matrix_message(room_id, render_manager_task_message(t))
            else:
                await send_matrix_message(room_id, msg.payload.get("text") or _pretty_json(msg.payload))
            await _mark_sent(conn, msg.id)
            return

        if msg.channel == "webpush":
            notification = render_push_payload(msg.template, msg.payload)
            manager_user_id = notification.get("manager_user_id") or msg.payload.get("manager_user_id") or msg.recipient_address
            if not manager_user_id:
                raise RuntimeError("manager_user_id is required for webpush channel")
            await send_webpush_many(conn, str(manager_user_id), notification)
            await _mark_sent(conn, msg.id)
            return

        if msg.channel == "email":
            manager_user_id = msg.payload.get("manager_user_id") or msg.recipient_address
            if not manager_user_id:
                raise RuntimeError("manager_user_id is required for email channel")
            email = await _load_user_email(conn, str(manager_user_id))
            if not email:
                raise RuntimeError("manager email not found")
            notif = render_push_payload(msg.template, msg.payload)
            await send_email_message(email, notif.get("title") or "ITCS", notif.get("body") or "Новое уведомление")
            await _mark_sent(conn, msg.id)
            return

        raise RuntimeError(f"Unsupported channel: {msg.channel}")


async def run_once(pool: asyncpg.Pool) -> Tuple[int, int]:
    sent = 0
    failed = 0
    async with pool.acquire() as conn:
        batch = await _fetch_and_lock_batch(conn)
    for msg in batch:
        try:
            await _process_message(pool, msg)
            sent += 1
            log.info("sent id=%s channel=%s template=%s", msg.id, msg.channel, msg.template)
        except Exception as e:
            failed += 1
            async with pool.acquire() as conn:
                await _mark_failed(conn, msg.id, msg.attempts + 1, str(e))
            log.exception("failed id=%s channel=%s template=%s", msg.id, msg.channel, msg.template)
    return sent, failed


async def run_forever() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is empty")
    if not DSN.startswith("postgres"):
        raise RuntimeError(f"Invalid DSN after normalization: {DSN[:80]}...")
    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=10, command_timeout=30)
    try:
        log.info("notifier started (batch=%s interval=%ss)", BATCH_SIZE, POLL_INTERVAL_SEC)
        while True:
            try:
                s, _ = await run_once(pool)
                if s == 0:
                    await asyncio.sleep(POLL_INTERVAL_SEC)
            except Exception:
                log.exception("loop error")
                await asyncio.sleep(POLL_INTERVAL_SEC)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_forever())
