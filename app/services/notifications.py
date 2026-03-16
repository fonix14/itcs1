from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationOutbox, Task, Store, User


def _fmt_dt(dt: Any) -> str:
    if not dt:
        return "—"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)


def _s(v: Any) -> str:
    if v is None:
        return "—"
    s = str(v).strip()
    return s if s else "—"


async def enqueue_digest(
    session: AsyncSession,
    upload_id,
    created: int,
    updated: int,
    invalid: int,
    trust: str,
) -> None:
    """
    Legacy digest (single message).
    Kept for compatibility, but Stage 4.3 uses enqueue_variant_b().
    """
    text = (
        "📥 Импорт завершён\n\n"
        f"Новых: {created}\n"
        f"Обновлено: {updated}\n"
        f"Ошибок: {invalid}\n"
        f"Trust: {trust}"
    )

    session.add(
        NotificationOutbox(
            channel="matrix",
            recipient_address="",
            template="digest_after_upload",
            payload={"text": text, "upload_id": str(upload_id)},
            dedupe_key=f"digest_{upload_id}",
            status="queued",
        )
    )


async def enqueue_variant_b(
    session: AsyncSession,
    upload_id,
    *,
    created: int,
    updated: int,
    invalid: int,
    trust: str,
    created_task_ids: List[str],
) -> Dict[str, int]:
    """
    Stage 4.3 Variant B:
      - one digest per manager per upload
      - immediate notifications only for NEW tasks

    Dedup keys:
      digest:{upload_id}:{manager_id}
      newtask:{task_id}:{manager_id}
    """
    dig = await _enqueue_manager_digests(
        session=session,
        upload_id=upload_id,
        created=created,
        updated=updated,
        invalid=invalid,
        trust=trust,
        created_task_ids=created_task_ids,
    )
    newc = await _enqueue_new_tasks(
        session=session,
        upload_id=upload_id,
        created_task_ids=created_task_ids,
    )
    return {"digests": dig, "new_tasks": newc}


async def _enqueue_manager_digests(
    session: AsyncSession,
    upload_id,
    *,
    created: int,
    updated: int,
    invalid: int,
    trust: str,
    created_task_ids: List[str],
) -> int:
    # managers who have at least one store assigned
    res = await session.execute(
        select(User.id, User.full_name)
        .join(Store, Store.assigned_user_id == User.id)
        .where(User.role == "manager")
        .group_by(User.id, User.full_name)
    )
    managers = res.all()

    # prefetch created per manager
    created_by_manager: Dict[str, int] = {}
    if created_task_ids:
        res2 = await session.execute(
            select(Store.assigned_user_id, func.count(Task.id))
            .join(Store, Store.id == Task.store_id)
            .where(Task.id.in_([UUID(x) for x in created_task_ids]))
            .where(Store.assigned_user_id.is_not(None))
            .group_by(Store.assigned_user_id)
        )
        for mid, cnt in res2.all():
            created_by_manager[str(mid)] = int(cnt)

    inserted = 0
    for manager_id, manager_name in managers:
        mid = str(manager_id)
        new_for_manager = created_by_manager.get(mid, 0)

        # total active tasks for manager (quick signal)
        res3 = await session.execute(
            select(func.count(Task.id))
            .join(Store, Store.id == Task.store_id)
            .where(Store.assigned_user_id == manager_id)
            .where(Task.status != "resolved")
        )
        total_open = int(res3.scalar_one() or 0)

        text = (
            f"📥 Импорт завершён — {manager_name}\n\n"
            f"Новых (твоих): {new_for_manager}\n"
            f"Новых (всего): {created}\n"
            f"Обновлено: {updated}\n"
            f"Ошибок: {invalid}\n"
            f"Открытых задач у тебя: {total_open}\n"
            f"Trust: {trust}"
        )

        session.add(
            NotificationOutbox(
                channel="matrix",
                recipient_address="",  # notifier fallback to MATRIX_ROOM_ID
                template="manager_digest",
                payload={
                    "text": text,
                    "upload_id": str(upload_id),
                    "manager_user_id": mid,
                    "kind": "digest",
                },
                dedupe_key=f"digest:{upload_id}:{mid}",
                status="queued",
            )
        )
        inserted += 1

    return inserted


async def _enqueue_new_tasks(
    session: AsyncSession,
    upload_id,
    *,
    created_task_ids: List[str],
) -> int:
    if not created_task_ids:
        return 0

    # load tasks + stores + managers for the created ids
    ids = [UUID(x) for x in created_task_ids]
    res = await session.execute(
        select(
            Task.id,
            Task.portal_task_id,
            Task.status,
            Task.sla,
            Task.created_at,
            Store.store_no,
            Store.assigned_user_id,
            User.full_name,
        )
        .join(Store, Store.id == Task.store_id)
        .join(User, User.id == Store.assigned_user_id)
        .where(Task.id.in_(ids))
    )

    inserted = 0
    for (
        task_id,
        portal_task_id,
        status,
        sla,
        created_at,
        store_no,
        manager_id,
        manager_name,
    ) in res.all():
        tid = str(task_id)
        mid = str(manager_id)

        text = "\n".join(
            [
                f"🆕 Новая заявка — {manager_name}",
                f"🆔 Портал: {_s(portal_task_id)}",
                f"🏪 Магазин: {_s(store_no)}",
                f"📌 Статус: {_s(status)}",
                f"⏳ SLA: {_s(sla)}",
                f"🕒 Создано: {_fmt_dt(created_at)}",
            ]
        )

        session.add(
            NotificationOutbox(
                channel="matrix",
                recipient_address="",  # notifier fallback to MATRIX_ROOM_ID
                template="manager_task_new",
                payload={
                    "text": text,
                    "upload_id": str(upload_id),
                    "task_id": tid,
                    "manager_user_id": mid,
                    "kind": "new_task",
                },
                dedupe_key=f"newtask:{tid}:{mid}",
                status="queued",
            )
        )
        inserted += 1

    return inserted
