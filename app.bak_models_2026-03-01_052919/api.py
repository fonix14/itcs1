from __future__ import annotations
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import Store, Task, TaskInternalState, Upload, Anomaly, AnomalyStatus
from app.schemas import (
    StoreOut, TaskOut, Me, AcceptIn, TaskInternalOut,
    UploadOut, ImportReport, AnomalyOut, TrustSummary
)
from app.security import get_actor
from app.settings import settings
from app.importer.service import import_xlsx_soft, compute_trust
from app.notifications.outbox import enqueue_digest_after_upload

router = APIRouter(prefix="/api")

async def get_db(actor=Depends(get_actor)) -> AsyncSession:
    user_id, role = actor
    async with db_session(user_id, role) as s:
        yield s

def require_dispatcher(actor=Depends(get_actor)):
    uid, role = actor
    if role != "dispatcher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dispatcher only")
    return uid, role

@router.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    await db.execute(text("select 1"))
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@router.get("/self_check")
async def self_check(actor=Depends(get_actor), db: AsyncSession = Depends(get_db)):
    user_id, role = actor
    r = await db.execute(text("select current_setting('app.user_id', true) as uid, current_setting('app.role', true) as role"))
    row = r.mappings().one()
    return {"actor": {"user_id": user_id, "role": role}, "db": {"user_id": row["uid"], "role": row["role"]}}

@router.get("/me", response_model=Me)
async def me(actor=Depends(get_actor)):
    uid, role = actor
    return Me(user_id=UUID(uid), role=role)

@router.get("/stores", response_model=list[StoreOut])
async def list_stores(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Store).order_by(Store.store_no))
    return [StoreOut.model_validate(s, from_attributes=True) for s in res.scalars().all()]

@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Task).order_by(Task.last_seen_at.desc()).limit(500))
    return [TaskOut.model_validate(t, from_attributes=True) for t in res.scalars().all()]

@router.post("/tasks/{task_id}/accept", response_model=TaskInternalOut)
async def accept_task(task_id: UUID, body: AcceptIn, actor=Depends(get_actor), db: AsyncSession = Depends(get_db)):
    user_id, _role = actor
    now = datetime.utcnow()
    res = await db.execute(select(TaskInternalState).where(TaskInternalState.task_id == task_id))
    st = res.scalar_one_or_none()
    if not st:
        st = TaskInternalState(task_id=task_id, accepted_at=now, accepted_by_user_id=UUID(user_id), last_comment=body.comment, updated_at=now)
        db.add(st)
    else:
        st.accepted_at = st.accepted_at or now
        st.accepted_by_user_id = st.accepted_by_user_id or UUID(user_id)
        st.last_comment = body.comment or st.last_comment
        st.updated_at = now
    await db.commit()
    await db.refresh(st)
    return TaskInternalOut.model_validate(st, from_attributes=True)

# -------- Stage 2 endpoints (dispatcher-only) --------

@router.post("/uploads", response_model=ImportReport)
async def upload_xlsx(
    _actor=Depends(require_dispatcher),
    db: AsyncSession = Depends(get_db),
    profile_id: str = Form(default="default"),
    file: UploadFile = File(...),
):
    b = await file.read()
    result = await import_xlsx_soft(db, file.filename or "upload.xlsx", b, profile_id)
    if not result.get('idempotent'):
        await enqueue_digest_after_upload(
            db,
            result['upload'].id,
            created_tasks=int(result.get('created_tasks') or 0),
            updated_tasks=int(result.get('updated_tasks') or 0),
            anomalies_created=int(result.get('anomalies_created') or 0),
            trust_level=str(result['trust']['trust_level']),
            trust_reasons=list(result['trust'].get('reasons') or []),
        )
        await db.commit()
    up: Upload = result["upload"]
    trust = result["trust"]
    return ImportReport(
        upload=UploadOut.model_validate(up, from_attributes=True),
        anomalies_created=int(result["anomalies_created"]),
        idempotent=bool(result["idempotent"]),
        trust_level=trust["trust_level"],
        trust_reasons=trust["reasons"],
    )

@router.get("/uploads", response_model=list[UploadOut])
async def list_uploads(_actor=Depends(require_dispatcher), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Upload).order_by(Upload.uploaded_at.desc()).limit(50))
    return [UploadOut.model_validate(u, from_attributes=True) for u in res.scalars().all()]

@router.get("/anomalies", response_model=list[AnomalyOut])
async def list_anomalies(_actor=Depends(require_dispatcher), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Anomaly).where(Anomaly.status == AnomalyStatus.open).order_by(Anomaly.due_at.asc().nulls_last()).limit(200))
    return [AnomalyOut.model_validate(a, from_attributes=True) for a in res.scalars().all()]

@router.get("/metrics/trust", response_model=TrustSummary)
async def trust_summary(_actor=Depends(require_dispatcher), db: AsyncSession = Depends(get_db)):
    t = await compute_trust(db)
    return TrustSummary(**t)


from app.models import DeviceSubscription, NotificationOutbox
from app.schemas import PushSubscriptionIn, OutboxItemOut
from sqlalchemy.dialects.postgresql import insert

@router.post("/push/subscribe")
async def push_subscribe(body: PushSubscriptionIn, actor=Depends(get_actor), db: AsyncSession = Depends(get_db)):
    user_id, _role = actor
    stmt = insert(DeviceSubscription).values(
        user_id=user_id,
        endpoint=body.endpoint,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        is_active=True,
    ).on_conflict_do_update(
        index_elements=[DeviceSubscription.endpoint],
        set_={"user_id": user_id, "p256dh": body.keys.p256dh, "auth": body.keys.auth, "is_active": True},
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}

@router.post("/push/unsubscribe")
async def push_unsubscribe(endpoint: str = Form(...), actor=Depends(get_actor), db: AsyncSession = Depends(get_db)):
    user_id, _role = actor
    res = await db.execute(select(DeviceSubscription).where(DeviceSubscription.endpoint == endpoint))
    s = res.scalar_one_or_none()
    if s and str(s.user_id) == str(user_id):
        s.is_active = False
        await db.commit()
    return {"ok": True}

@router.get("/outbox", response_model=list[OutboxItemOut])
async def list_outbox(_actor=Depends(require_dispatcher), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(NotificationOutbox).order_by(NotificationOutbox.created_at.desc()).limit(200))
    items = res.scalars().all()
    return [OutboxItemOut.model_validate(i, from_attributes=True) for i in items]

# -------- Stage 4: Notification Engine (dispatcher-only) --------

from app.models import NotificationWorkerState


@router.get("/notifications/health")
async def notifications_health(_actor=Depends(require_dispatcher), db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        text(
            """
            SELECT
                SUM(CASE WHEN status='queued' THEN 1 ELSE 0 END) AS queued,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status='dead' THEN 1 ELSE 0 END) AS dead,
                MAX(sent_at) AS last_sent_item_at
            FROM notification_outbox
            """
        )
    )
    row = q.mappings().one()

    st = await db.get(NotificationWorkerState, 1)

    now = datetime.utcnow()
    last_tick = st.last_tick_at if st else None
    worker_alive = bool(
        last_tick and (now - last_tick.replace(tzinfo=None)).total_seconds() < settings.notifier_worker_alive_sec
    )

    return {
        "queued": int(row["queued"] or 0),
        "failed": int(row["failed"] or 0),
        "dead": int(row["dead"] or 0),
        "last_sent_item_at": row["last_sent_item_at"].isoformat() if row["last_sent_item_at"] else None,
        "last_tick_at": last_tick.isoformat() if last_tick else None,
        "last_sent_at": st.last_sent_at.isoformat() if st and st.last_sent_at else None,
        "last_error": st.last_error if st else None,
        "worker_alive": worker_alive,
    }


@router.get("/notifications/outbox")
async def notifications_outbox(
    status: str = "failed",
    _actor=Depends(require_dispatcher),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        text(
            """
            SELECT id, created_at, channel, recipient_address, template, status, attempts,
                   next_retry_at, last_error, dedupe_key, sent_at
            FROM notification_outbox
            WHERE status = :status
            ORDER BY created_at DESC
            LIMIT 200
            """
        ),
        {"status": status},
    )
    return [dict(r) for r in res.mappings().all()]
