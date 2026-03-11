from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationOutbox, HealthState
from app.settings import settings


def _portal_upload_url(upload_id: UUID) -> str:
    base = (settings.portal_base_url or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/dispatcher/uploads/{upload_id}"


async def enqueue_digest_after_upload(db: AsyncSession, upload_id: UUID, *, created_tasks: int, updated_tasks: int, anomalies_created: int, trust_level: str, trust_reasons: list[str]) -> None:
    """Create exactly ONE outbox row for Matrix room digest after upload.

    Idempotency: dedupe_key is unique.
    Matrix idempotency: txnId will be outbox.id (worker).
    """
    room_id = settings.matrix_room_id
    if not room_id:
        # If Matrix isn't configured yet, still enqueue (recipient empty) so dispatcher can see queue.
        room_id = ""

    payload = {
        "upload_id": str(upload_id),
        "created": int(created_tasks),
        "updated": int(updated_tasks),
        "anomalies": int(anomalies_created),
        "trust_level": trust_level,
        "reasons": trust_reasons or [],
        "url": _portal_upload_url(upload_id),
    }

    dedupe_key = f"digest:{upload_id}:room:{room_id}"

    stmt = insert(NotificationOutbox).values(
        channel="matrix",
        recipient_address=room_id,
        template="digest_after_upload",
        payload=payload,
        status="queued",
        attempts=0,
        next_retry_at=datetime.utcnow(),
        dedupe_key=dedupe_key,
    ).on_conflict_do_nothing(index_elements=[NotificationOutbox.dedupe_key])

    await db.execute(stmt)


async def maybe_enqueue_daily_health(db: AsyncSession, *, now_utc: datetime) -> bool:
    """Create daily health notification if system is degraded.

    Returns True if an outbox item was created.

    Policy:
    - max 1 per day
    - only if trust != GREEN OR no_import threshold / overdue anomalies (already in trust reasons)
    - dedupe_key includes date + trust_level

    NOTE: this function is intended to be called by notifier worker (not API).
    """

    level = trust.get("trust_level")
    reasons = trust.get("reasons") or []

    hs = await db.get(HealthState, 1)
    if hs is None:
        hs = HealthState(id=1)
        db.add(hs)
        await db.flush()

    hs.last_trust_level = level
    hs.last_reasons = reasons
    hs.updated_at = now_utc

    if level == "GREEN":
        await db.flush()
        return False

    # Daily limiter: 1 per day
    day = now_utc.date().isoformat()
    room_id = settings.matrix_room_id or ""
    dedupe_key = f"health:{day}:room:{room_id}:{level}"

    payload = {
        "type": "daily_health",
        "trust_level": level,
        "reasons": reasons,
        "no_import_hours": trust.get("no_import_hours"),
        "pending_anomalies": trust.get("pending_anomalies"),
        "url": (settings.portal_base_url or "").rstrip("/") + "/dispatcher/health" if settings.portal_base_url else "",
    }

    stmt = insert(NotificationOutbox).values(
        channel="matrix",
        recipient_address=room_id,
        template="daily_health",
        payload=payload,
        status="queued",
        attempts=0,
        next_retry_at=now_utc,
        dedupe_key=dedupe_key,
    ).on_conflict_do_nothing(index_elements=[NotificationOutbox.dedupe_key])

    await db.execute(stmt)

    return True
