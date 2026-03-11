from __future__ import annotations

import asyncio
import json
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# =========================
# Config (env-driven)
# =========================

def _env(*names: str, default: Optional[str] = None) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v is not None and str(v).strip() != "":
            return v
    return default


def _as_bool(v: Optional[str], default: bool = True) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() not in ("0", "false", "no", "off", "")


DATABASE_URL = _env("DATABASE_URL", "SQLALCHEMY_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

# Notifier enable switch: allows running stack without Matrix config (no crash loops)
NOTIFIER_ENABLED = _as_bool(_env("NOTIFIER_ENABLED", default="1"), default=True)

# Matrix config
MATRIX_BASE_URL = (_env("MATRIX_BASE_URL", "MATRIX_HOMESERVER", "MATRIX_SERVER_URL") or "").rstrip("/")
MATRIX_ACCESS_TOKEN = _env("MATRIX_ACCESS_TOKEN", "MATRIX_TOKEN")
DEFAULT_MATRIX_ROOM_ID = _env("MATRIX_ROOM_ID", default="")

# Notifier tuning
BATCH_SIZE = int(_env("NOTIFIER_BATCH", "OUTBOX_BATCH_SIZE", default="20"))
POLL_INTERVAL_SEC = int(_env("NOTIFIER_INTERVAL_SEC", "OUTBOX_POLL_INTERVAL_SEC", default="10"))
SEND_DELAY_SEC = float(_env("NOTIFIER_SEND_DELAY_SEC", default="0.7"))  # rate-limit guard
MAX_ATTEMPTS = int(_env("NOTIFIER_MAX_ATTEMPTS", "OUTBOX_MAX_ATTEMPTS", default="10"))
SENDING_STUCK_MIN = int(_env("NOTIFIER_SENDING_STUCK_MIN", "OUTBOX_SENDING_STUCK_MINUTES", default="10"))

GUARD_CHANNEL = "matrix"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# =========================
# DB models (row mapping)
# =========================

@dataclass
class OutboxRow:
    id: str
    channel: str
    recipient_address: str
    template: str
    payload: dict[str, Any]
    attempts: int


# =========================
# SQL helpers
# =========================

async def guard_get(db: AsyncSession) -> tuple[str, Optional[datetime]]:
    row = (
        await db.execute(
            text(
                """
        SELECT state, open_until
        FROM outbox_guard_state
        WHERE id=1 AND channel=:ch
        """
            ),
            {"ch": GUARD_CHANNEL},
        )
    ).mappings().first()

    if not row:
        return ("CLOSED", None)
    return (row["state"], row["open_until"])


async def guard_open(db: AsyncSession, seconds: int, err: str) -> None:
    await db.execute(
        text(
            """
        UPDATE outbox_guard_state
        SET state='OPEN',
            open_until = now() + (:s || ' seconds')::interval,
            last_error = left(:err, 8000),
            consecutive_failures = consecutive_failures + 1,
            last_failure_at = now(),
            updated_at = now()
        WHERE id=1 AND channel=:ch
        """
        ),
        {"s": int(seconds), "err": err, "ch": GUARD_CHANNEL},
    )


async def guard_half_open(db: AsyncSession) -> None:
    await db.execute(
        text(
            """
        UPDATE outbox_guard_state
        SET state='HALF_OPEN',
            updated_at = now()
        WHERE id=1 AND channel=:ch
        """
        ),
        {"ch": GUARD_CHANNEL},
    )


async def guard_close(db: AsyncSession) -> None:
    await db.execute(
        text(
            """
        UPDATE outbox_guard_state
        SET state='CLOSED',
            open_until = NULL,
            consecutive_failures = 0,
            last_success_at = now(),
            updated_at = now()
        WHERE id=1 AND channel=:ch
        """
        ),
        {"ch": GUARD_CHANNEL},
    )


async def watchdog_sending_stuck(db: AsyncSession) -> int:
    res = await db.execute(
        text(
            f"""
        UPDATE notification_outbox
        SET status='failed',
            next_retry_at = now() + interval '300 seconds',
            last_error = left(coalesce(last_error,'') || E'\\n[WATCHDOG] sending stuck', 8000),
            sending_started_at = NULL
        WHERE status='sending'
          AND sending_started_at IS NOT NULL
          AND sending_started_at < now() - interval '{int(SENDING_STUCK_MIN)} minutes'
        RETURNING id
        """
        )
    )
    return len(res.fetchall())


async def claim_batch(db: AsyncSession, batch_size: int) -> list[OutboxRow]:
    sql = text(
        """
        WITH cte AS (
          SELECT id
          FROM notification_outbox
          WHERE status IN ('queued','failed')
            AND (next_retry_at IS NULL OR next_retry_at <= now())
          ORDER BY
            COALESCE(next_retry_at, created_at) ASC,
            created_at ASC
          FOR UPDATE SKIP LOCKED
          LIMIT :batch
        )
        UPDATE notification_outbox o
        SET status='sending',
            sending_started_at = now()
        FROM cte
        WHERE o.id = cte.id
        RETURNING
          o.id::text AS id,
          o.channel,
          o.recipient_address,
          o.template,
          o.payload,
          o.attempts
        """
    )
    res = await db.execute(sql, {"batch": batch_size})
    rows: list[OutboxRow] = []
    for r in res.mappings().all():
        payload = r["payload"] if isinstance(r["payload"], dict) else {}
        rows.append(
            OutboxRow(
                id=r["id"],
                channel=r["channel"],
                recipient_address=r["recipient_address"] or "",
                template=r["template"],
                payload=payload or {},
                attempts=int(r["attempts"] or 0),
            )
        )
    return rows


async def mark_sent(db: AsyncSession, outbox_id: str) -> None:
    await db.execute(
        text(
            """
        UPDATE notification_outbox
        SET status='sent',
            sent_at=now(),
            last_error=NULL,
            sending_started_at=NULL
        WHERE id::text=:id
        """
        ),
        {"id": outbox_id},
    )


def _calc_backoff_seconds(attempts_after_increment: int) -> int:
    if attempts_after_increment <= 1:
        return 60
    if attempts_after_increment == 2:
        return 180
    if attempts_after_increment == 3:
        return 600
    return 1800


async def mark_failed(
    db: AsyncSession,
    outbox_id: str,
    err: str,
    retry_after_seconds: Optional[int] = None,
) -> None:
    await db.execute(
        text(
            """
        UPDATE notification_outbox
        SET attempts = attempts + 1,
            status = CASE WHEN attempts + 1 >= :max_attempts THEN 'dead' ELSE 'failed' END,
            last_error = left(coalesce(last_error,'') || E'\n' || :err, 8000),
            sending_started_at = NULL
        WHERE id::text=:id
        """
        ),
        {"id": outbox_id, "err": err, "max_attempts": MAX_ATTEMPTS},
    )

    res = await db.execute(
        text("SELECT attempts, status FROM notification_outbox WHERE id::text=:id"),
        {"id": outbox_id},
    )
    row = res.mappings().first()
    if not row:
        return

    attempts_now = int(row["attempts"] or 0)
    status = row["status"]

    if status == "dead":
        await db.execute(
            text("UPDATE notification_outbox SET next_retry_at = now() WHERE id::text=:id"),
            {"id": outbox_id},
        )
        return

    backoff = int(retry_after_seconds or _calc_backoff_seconds(attempts_now))
    await db.execute(
        text(
            """
        UPDATE notification_outbox
        SET next_retry_at = now() + (:b || ' seconds')::interval
        WHERE id::text=:id
        """
        ),
        {"id": outbox_id, "b": backoff},
    )


# =========================
# Matrix sender (v3)
# =========================

class RateLimitError(Exception):
    def __init__(self, retry_after_seconds: int, message: str = "rate limited"):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


async def matrix_send(room_id: str, message: dict[str, Any]) -> None:
    txn_id = uuid.uuid4().hex
    url = f"{MATRIX_BASE_URL}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
    headers = {"Authorization": f"Bearer {MATRIX_ACCESS_TOKEN}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.put(url, headers=headers, json=message)

    if r.status_code == 429:
        retry_after = 120
        ra = r.headers.get("Retry-After")
        if ra:
            try:
                retry_after = int(float(ra))
            except Exception:
                pass
        else:
            try:
                data = r.json()
                ms = data.get("retry_after_ms")
                if isinstance(ms, (int, float)) and ms > 0:
                    retry_after = max(1, int(ms / 1000))
            except Exception:
                pass
        raise RateLimitError(retry_after_seconds=retry_after, message=f"Matrix 429 (retry_after={retry_after}s)")

    if r.status_code >= 500:
        raise RuntimeError(f"Matrix {r.status_code}: server error")

    if r.status_code >= 400:
        raise RuntimeError(f"Matrix {r.status_code}: {r.text[:300]}")


def build_matrix_message(row: OutboxRow) -> tuple[str, dict[str, Any]]:
    room_id = row.recipient_address.strip() or DEFAULT_MATRIX_ROOM_ID
    p = row.payload or {}

    # stable fallback keys
    text_body = p.get("text") or p.get("body") or p.get("message")
    if not text_body:
        text_body = f"[{row.template}] " + json.dumps(p, ensure_ascii=False)[:1500]

    html_body = p.get("html")

    msg: dict[str, Any] = {"msgtype": "m.text", "body": str(text_body)}
    if html_body:
        msg["format"] = "org.matrix.custom.html"
        msg["formatted_body"] = str(html_body)

    return room_id, msg


# =========================
# Main loop
# =========================

async def run() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=5)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"notifier started (batch={BATCH_SIZE} interval={POLL_INTERVAL_SEC}s) [HARDENED+GUARD]")

    # If Matrix config is missing, don't crash-loop; just disable sending.
    if NOTIFIER_ENABLED and (not MATRIX_BASE_URL or not MATRIX_ACCESS_TOKEN):
        print("WARN: Matrix config missing. Set MATRIX_BASE_URL and MATRIX_ACCESS_TOKEN (or set NOTIFIER_ENABLED=0).")
        NOTIFIER_OK = False
    else:
        NOTIFIER_OK = NOTIFIER_ENABLED

    while True:
        await asyncio.sleep(random.uniform(0.05, 0.2))

        async with Session() as db:
            try:
                stuck = await watchdog_sending_stuck(db)
                if stuck:
                    await db.commit()

                state, open_until = await guard_get(db)
                now = utcnow()

                if state == "OPEN" and open_until and open_until > now:
                    await db.commit()
                    await asyncio.sleep(5)
                    continue

                if state == "OPEN" and open_until and open_until <= now:
                    await guard_half_open(db)
                    await db.commit()
                    state = "HALF_OPEN"

                # If sending disabled, do not claim anything (keeps DB quiet)
                if not NOTIFIER_OK:
                    await db.commit()
                    await asyncio.sleep(POLL_INTERVAL_SEC)
                    continue

                batch = await claim_batch(db, batch_size=(1 if state == "HALF_OPEN" else BATCH_SIZE))
                await db.commit()

            except Exception:
                await db.rollback()
                await asyncio.sleep(2)
                continue

        if not batch:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue

        for row in batch:
            await asyncio.sleep(SEND_DELAY_SEC)

            if row.channel != "matrix":
                async with Session() as db:
                    try:
                        await mark_failed(db, row.id, f"Unsupported channel: {row.channel}", retry_after_seconds=3600)
                        await db.commit()
                    except Exception:
                        await db.rollback()
                continue

            room_id, msg = build_matrix_message(row)
            if not room_id:
                async with Session() as db:
                    try:
                        await mark_failed(db, row.id, "Missing recipient_address and MATRIX_ROOM_ID", retry_after_seconds=3600)
                        await db.commit()
                    except Exception:
                        await db.rollback()
                continue

            async with Session() as db:
                try:
                    await matrix_send(room_id, msg)
                    await mark_sent(db, row.id)
                    await guard_close(db)
                    await db.commit()

                except RateLimitError as e:
                    try:
                        await mark_failed(db, row.id, str(e), retry_after_seconds=e.retry_after_seconds)
                        await guard_open(db, seconds=max(30, int(e.retry_after_seconds)), err=str(e))
                        await db.commit()
                    except Exception:
                        await db.rollback()
                    break

                except Exception as e:
                    err = f"Send failed: {repr(e)}"
                    try:
                        await mark_failed(db, row.id, err)
                        if "Matrix 5" in err or "timeout" in err.lower():
                            await guard_open(db, seconds=300, err=err)
                        await db.commit()
                    except Exception:
                        await db.rollback()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
