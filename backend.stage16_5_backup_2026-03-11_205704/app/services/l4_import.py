import hashlib
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, Store, Anomaly


def parse_date(value):
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def generate_portal_task_id(
    store_no: str,
    incident_type: str,
    text: str,
    changed_at: Optional[datetime],
    sla: Optional[datetime],
) -> str:
    base = (
        (store_no or "").strip()
        + (incident_type or "").strip()
        + (text or "").strip()
        + (changed_at.isoformat() if changed_at else "")
        + (sla.isoformat() if sla else "")
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def process_l4_row(session: AsyncSession, row: dict, upload_id) -> Tuple[str, Optional[str]]:
    """
    Returns:
      ("created"|"updated"|"invalid", task_id or None)

    NOTE: We flush on created to get task_id for Variant-B notifications.
    """
    try:
        store_no = str(row.get("Номер магазина", "")).strip()
        incident_type = str(row.get("Тип инцидента", "")).strip()
        text = str(row.get("Текст обращения", "")).strip()

        if not store_no or not incident_type or not text:
            return "invalid", None

        changed_at = parse_date(row.get("Дата изменения"))
        sla_control = parse_date(row.get("Контроль до"))
        sla_default = parse_date(row.get("Дата SLA"))
        sla_dt = sla_control or sla_default

        # We store SLA as a string in current MVP schema
        sla_value = sla_dt.isoformat() if sla_dt else (str(row.get("SLA") or row.get("sla") or "").strip() or None)

        portal_task_id = generate_portal_task_id(
            store_no, incident_type, text, changed_at, sla_dt
        )

        result = await session.execute(
            select(Store).where(Store.store_no == store_no)
        )
        store = result.scalar_one_or_none()

        if not store:
            session.add(
                Anomaly(
                    upload_id=upload_id,
                    code="MISSING_MANAGER",
                    severity="major",
                    description=f"Store {store_no} not mapped",
                )
            )
            return "invalid", None

        result = await session.execute(
            select(Task).where(Task.portal_task_id == portal_task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            t = Task(
                portal_task_id=portal_task_id,
                store_id=store.id,
                status=str(row.get("Статус") or row.get("status") or "new"),
                sla=sla_value,
                last_seen_at=datetime.utcnow(),
            )
            session.add(t)
            # flush to obtain UUID id
            await session.flush()
            return "created", str(t.id)
        else:
            task.status = str(row.get("Статус") or row.get("status") or task.status)
            task.sla = sla_value
            task.last_seen_at = datetime.utcnow()
            await session.flush()
            return "updated", str(task.id)

    except Exception:
        return "invalid", None
