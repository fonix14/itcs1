from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
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


def _queue(session: AsyncSession, *, channel: str, template: str, payload: dict, dedupe_key: str, recipient_address: str = "") -> None:
    session.add(NotificationOutbox(channel=channel, recipient_address=recipient_address, template=template, payload=payload, dedupe_key=dedupe_key, status="queued"))


async def enqueue_variant_b(session: AsyncSession, upload_id, *, created: int, updated: int, invalid: int, trust: str, created_task_ids: List[str]) -> Dict[str, int]:
    dig = await _enqueue_manager_digests(session, upload_id=upload_id, created=created, updated=updated, invalid=invalid, trust=trust, created_task_ids=created_task_ids)
    newc = await _enqueue_new_tasks(session, upload_id=upload_id, created_task_ids=created_task_ids)
    return {"digests": dig, "new_tasks": newc}


async def _enqueue_manager_digests(session: AsyncSession, upload_id, *, created: int, updated: int, invalid: int, trust: str, created_task_ids: List[str]) -> int:
    res = await session.execute(select(User.id, User.full_name).join(Store, Store.assigned_user_id == User.id).where(User.role == "manager").group_by(User.id, User.full_name))
    managers = res.all()
    created_by_manager: Dict[str, int] = {}
    if created_task_ids:
        res2 = await session.execute(select(Store.assigned_user_id, func.count(Task.id)).join(Store, Store.id == Task.store_id).where(Task.id.in_([UUID(x) for x in created_task_ids])).where(Store.assigned_user_id.is_not(None)).group_by(Store.assigned_user_id))
        for mid, cnt in res2.all():
            created_by_manager[str(mid)] = int(cnt)
    inserted = 0
    for manager_id, manager_name in managers:
        mid = str(manager_id)
        new_for_manager = created_by_manager.get(mid, 0)
        res3 = await session.execute(select(func.count(Task.id)).join(Store, Store.id == Task.store_id).where(Store.assigned_user_id == manager_id).where(Task.status != "closed"))
        total_open = int(res3.scalar_one() or 0)
        text = (f"📥 Импорт завершён — {manager_name}\n\nНовых (твоих): {new_for_manager}\nНовых (всего): {created}\nОбновлено: {updated}\nОшибок: {invalid}\nОткрытых задач у тебя: {total_open}\nTrust: {trust}")
        payload = {"text": text, "upload_id": str(upload_id), "manager_user_id": mid, "kind": "digest"}
        _queue(session, channel="matrix", template="manager_digest", payload=payload, dedupe_key=f"digest:matrix:{upload_id}:{mid}")
        _queue(session, channel="webpush", template="manager_digest", payload=payload, dedupe_key=f"digest:webpush:{upload_id}:{mid}", recipient_address=mid)
        _queue(session, channel="email", template="manager_digest", payload=payload, dedupe_key=f"digest:email:{upload_id}:{mid}", recipient_address=mid)
        inserted += 3
    return inserted


async def _enqueue_new_tasks(session: AsyncSession, upload_id, *, created_task_ids: List[str]) -> int:
    if not created_task_ids:
        return 0
    ids = [UUID(x) for x in created_task_ids]
    res = await session.execute(select(Task.id, Task.portal_task_id, Task.status, Task.sla, Task.created_at, Store.store_no, Store.assigned_user_id, User.full_name).join(Store, Store.id == Task.store_id).join(User, User.id == Store.assigned_user_id).where(Task.id.in_(ids)))
    inserted = 0
    for task_id, portal_task_id, status, sla, created_at, store_no, manager_id, manager_name in res.all():
        tid = str(task_id)
        mid = str(manager_id)
        text = "\n".join([f"🆕 Новая заявка — {manager_name}", f"🆔 Портал: {_s(portal_task_id)}", f"🏪 Магазин: {_s(store_no)}", f"📌 Статус: {_s(status)}", f"⏳ SLA: {_s(sla)}", f"🕒 Создано: {_fmt_dt(created_at)}"])
        payload = {"text": text, "upload_id": str(upload_id), "task_id": tid, "portal_task_id": _s(portal_task_id), "store_no": _s(store_no), "manager_user_id": mid, "kind": "new_task"}
        _queue(session, channel="matrix", template="manager_task_new", payload=payload, dedupe_key=f"newtask:matrix:{tid}:{mid}")
        _queue(session, channel="webpush", template="manager_task_new", payload=payload, dedupe_key=f"newtask:webpush:{tid}:{mid}", recipient_address=mid)
        _queue(session, channel="email", template="manager_task_new", payload=payload, dedupe_key=f"newtask:email:{tid}:{mid}", recipient_address=mid)
        inserted += 3
    return inserted
