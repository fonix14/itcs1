from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(prefix="/api/ops", tags=["ops_risk_engine"])


def compute_risk(sla_at, internal_status: str | None) -> str:
    status = (internal_status or "new").strip().lower()
    if status == "done":
        return "none"

    if sla_at is None:
        return "none"

    now = datetime.now(timezone.utc)

    if sla_at < now:
        return "overdue"

    if sla_at <= now + timedelta(hours=24):
        return "warning"

    return "normal"


@router.post("/risk-scan")
async def risk_scan(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""
        select
            t.id::text as task_id,
            t.sla_due_at,
            coalesce(t.internal_status, 'new') as internal_status
        from tasks t
    """))
    items = rows.mappings().all()

    current_rows = await db.execute(text("""
        select
            task_id::text as task_id,
            current_risk
        from task_risk_state
    """))
    current_map = {r["task_id"]: r["current_risk"] for r in current_rows.mappings().all()}

    scanned = 0
    changed = 0
    inserted = 0

    for item in items:
        scanned += 1
        task_id = item["task_id"]
        sla_at = item["sla_due_at"]
        internal_status = item["internal_status"]
        new_risk = compute_risk(sla_at, internal_status)
        prev_risk = current_map.get(task_id)

        if prev_risk is None:
            await db.execute(text("""
                insert into task_risk_state (
                    task_id,
                    current_risk,
                    current_sla_at,
                    current_internal_status,
                    first_seen_at,
                    last_changed_at,
                    updated_at
                )
                values (
                    :task_id,
                    :current_risk,
                    :current_sla_at,
                    :current_internal_status,
                    now(),
                    now(),
                    now()
                )
            """), {
                "task_id": task_id,
                "current_risk": new_risk,
                "current_sla_at": sla_at,
                "current_internal_status": internal_status,
            })

            await db.execute(text("""
                insert into task_risk_events (
                    task_id,
                    previous_risk,
                    new_risk,
                    sla_at,
                    internal_status
                )
                values (
                    :task_id,
                    null,
                    :new_risk,
                    :sla_at,
                    :internal_status
                )
            """), {
                "task_id": task_id,
                "new_risk": new_risk,
                "sla_at": sla_at,
                "internal_status": internal_status,
            })

            inserted += 1
            continue

        if prev_risk != new_risk:
            await db.execute(text("""
                update task_risk_state
                set
                    current_risk = :current_risk,
                    current_sla_at = :current_sla_at,
                    current_internal_status = :current_internal_status,
                    last_changed_at = now(),
                    updated_at = now()
                where task_id = :task_id
            """), {
                "task_id": task_id,
                "current_risk": new_risk,
                "current_sla_at": sla_at,
                "current_internal_status": internal_status,
            })

            await db.execute(text("""
                insert into task_risk_events (
                    task_id,
                    previous_risk,
                    new_risk,
                    sla_at,
                    internal_status
                )
                values (
                    :task_id,
                    :previous_risk,
                    :new_risk,
                    :sla_at,
                    :internal_status
                )
            """), {
                "task_id": task_id,
                "previous_risk": prev_risk,
                "new_risk": new_risk,
                "sla_at": sla_at,
                "internal_status": internal_status,
            })

            changed += 1
        else:
            await db.execute(text("""
                update task_risk_state
                set
                    current_sla_at = :current_sla_at,
                    current_internal_status = :current_internal_status,
                    updated_at = now()
                where task_id = :task_id
            """), {
                "task_id": task_id,
                "current_sla_at": sla_at,
                "current_internal_status": internal_status,
            })

    await db.commit()

    return {
        "status": "ok",
        "scanned": scanned,
        "inserted": inserted,
        "changed": changed,
    }


@router.get("/risk-summary")
async def risk_summary(db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text("""
        select
            count(*) filter (
                where coalesce(internal_status, 'new') <> 'done'
            ) as active_total,
            count(*) filter (
                where coalesce(internal_status, 'new') <> 'done'
                  and sla_due_at is null
            ) as no_sla_count,
            count(*) filter (
                where coalesce(internal_status, 'new') <> 'done'
                  and sla_due_at is not null
                  and sla_due_at > now() + interval '24 hours'
            ) as normal_count,
            count(*) filter (
                where coalesce(internal_status, 'new') <> 'done'
                  and sla_due_at is not null
                  and sla_due_at >= now()
                  and sla_due_at <= now() + interval '24 hours'
            ) as warning_count,
            count(*) filter (
                where coalesce(internal_status, 'new') <> 'done'
                  and sla_due_at is not null
                  and sla_due_at < now()
            ) as overdue_count
        from tasks
    """))).mappings().first()

    return dict(row) if row else {
        "active_total": 0,
        "no_sla_count": 0,
        "normal_count": 0,
        "warning_count": 0,
        "overdue_count": 0,
    }


@router.get("/risk-feed")
async def risk_feed(limit: int = 50, db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""
        select
            t.id::text as id,
            t.portal_task_id,
            s.store_no,
            coalesce(u.display_name, u.full_name, u.email, '—') as manager_name,
            coalesce(t.internal_status, 'new') as internal_status,
            t.sla_due_at as sla_at,
            case
                when t.sla_due_at is null then 'none'
                when coalesce(t.internal_status, 'new') = 'done' then 'none'
                when t.sla_due_at < now() then 'overdue'
                when t.sla_due_at <= now() + interval '24 hours' then 'warning'
                else 'normal'
            end as risk_state
        from tasks t
        join stores s on s.id = t.store_id
        left join users u on u.id = coalesce(t.assigned_user_id, s.assigned_user_id)
        where coalesce(t.internal_status, 'new') <> 'done'
        order by
            case
                when t.sla_due_at is null then 2
                when t.sla_due_at < now() then 0
                when t.sla_due_at <= now() + interval '24 hours' then 1
                else 2
            end asc,
            t.sla_due_at asc nulls last
        limit :limit
    """), {"limit": limit})

    return [dict(x) for x in rows.mappings().all()]


@router.get("/manager-load")
async def manager_load(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""
        select
            coalesce(u.display_name, u.full_name, u.email, 'Не назначен') as manager_name,
            count(*) filter (
                where coalesce(t.internal_status, 'new') <> 'done'
            ) as active_count,
            count(*) filter (
                where coalesce(t.internal_status, 'new') <> 'done'
                  and t.sla_due_at is not null
                  and t.sla_due_at < now()
            ) as overdue_count,
            count(*) filter (
                where coalesce(t.internal_status, 'new') <> 'done'
                  and t.sla_due_at is not null
                  and t.sla_due_at >= now()
                  and t.sla_due_at <= now() + interval '24 hours'
            ) as warning_count
        from tasks t
        join stores s on s.id = t.store_id
        left join users u on u.id = coalesce(t.assigned_user_id, s.assigned_user_id)
        group by coalesce(u.display_name, u.full_name, u.email, 'Не назначен')
        order by overdue_count desc, warning_count desc, active_count desc, manager_name asc
    """))

    return [dict(x) for x in rows.mappings().all()]
