from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(prefix="/api/director", tags=["director_dashboard"])


def build_attention_items(
    *,
    trust_level: str,
    active_tasks: int,
    overdue_sla: int,
    pending_anomalies: int,
    invalid_ratio: float | None,
):
    items = []

    if trust_level == "RED":
        items.append({
            "level": "critical",
            "title": "Красная зона доверия к данным",
            "text": "Система требует немедленного внимания руководителя или диспетчера."
        })
    elif trust_level == "YELLOW":
        items.append({
            "level": "warning",
            "title": "Жёлтая зона доверия к данным",
            "text": "Есть признаки деградации качества данных или процессов."
        })

    if overdue_sla > 0:
        items.append({
            "level": "warning" if overdue_sla < 10 else "critical",
            "title": f"Просрочено по SLA: {overdue_sla}",
            "text": "Есть задачи, требующие оперативного контроля."
        })

    if pending_anomalies > 0:
        items.append({
            "level": "warning",
            "title": f"Открытые аномалии: {pending_anomalies}",
            "text": "Есть проблемы качества данных, которые ещё не закрыты."
        })

    if invalid_ratio is not None and invalid_ratio > 5:
        items.append({
            "level": "warning" if invalid_ratio <= 20 else "critical",
            "title": f"Невалидные строки: {invalid_ratio:.1f}%",
            "text": "Импорт содержит заметную долю проблемных строк."
        })

    if active_tasks == 0 and not items:
        items.append({
            "level": "ok",
            "title": "Критичных отклонений не обнаружено",
            "text": "Система выглядит стабильно, можно работать в штатном режиме."
        })

    return items[:5]


def build_exec_summary(
    *,
    trust_level: str,
    active_tasks: int,
    overdue_sla: int,
    pending_anomalies: int,
    invalid_ratio: float | None,
):
    parts = []

    if trust_level == "GREEN":
        parts.append("Система работает стабильно.")
    elif trust_level == "YELLOW":
        parts.append("Система требует повышенного внимания.")
    elif trust_level == "RED":
        parts.append("Система находится в критической зоне.")
    else:
        parts.append("Статус доверия к данным пока не определён.")

    parts.append(f"Активных задач: {active_tasks}.")
    parts.append(f"Просрочено по SLA: {overdue_sla}.")
    parts.append(f"Открытых аномалий: {pending_anomalies}.")

    if invalid_ratio is not None:
        parts.append(f"Невалидные строки в последней загрузке: {invalid_ratio:.1f}%.")

    return " ".join(parts)


@router.get("/dashboard")
async def director_dashboard(db: AsyncSession = Depends(get_db)):
    try:
        active_tasks_q = await db.execute(text("""
            select count(*) as cnt
            from tasks
            where status not in ('done','closed','cancelled')
        """))
        active_tasks = int(active_tasks_q.scalar_one())

        overdue_sla_q = await db.execute(text("""
            select count(*) as cnt
            from tasks
            where status not in ('done','closed','cancelled')
              and sla_due_at is not null
              and sla_due_at < now()
        """))
        overdue_sla = int(overdue_sla_q.scalar_one())

        latest_import_q = await db.execute(text("""
            select
                id,
                file_name as original_filename,
                profile_id as profile_code,
                uploaded_at,
                invalid_ratio
            from uploads
            order by uploaded_at desc
            limit 1
        """))
        latest_import = latest_import_q.mappings().first()

        trust_q = await db.execute(text("""
            select trust_level, calculated_at, pending_anomalies
            from health_state
            order by calculated_at desc
            limit 1
        """))
        trust = trust_q.mappings().first()

        top_stores_q = await db.execute(text("""
            select
                s.store_no,
                count(*) as open_tasks
            from tasks t
            join stores s on s.id = t.store_id
            where t.status not in ('done','closed','cancelled')
            group by s.store_no
            order by open_tasks desc, s.store_no asc
            limit 10
        """))
        top_stores = [dict(x) for x in top_stores_q.mappings().all()]

        manager_load_q = await db.execute(text("""
            select
                coalesce(u.full_name,u.email,'—') as full_name,
                count(*) as open_tasks
            from tasks t
            join stores s on s.id = t.store_id
            left join users u on u.id = s.assigned_user_id
            where t.status not in ('done','closed','cancelled')
            group by coalesce(u.full_name,u.email,'—')
            order by open_tasks desc, full_name asc
            limit 10
        """))
        manager_load = [dict(x) for x in manager_load_q.mappings().all()]

        latest_uploads_q = await db.execute(text("""
            select
                id,
                file_name as original_filename,
                profile_id as profile_code,
                uploaded_at,
                invalid_ratio,
                total_rows,
                valid_rows,
                invalid_rows
            from uploads
            order by uploaded_at desc
            limit 7
        """))
        latest_uploads = [dict(x) for x in latest_uploads_q.mappings().all()]

        uploads_daily_q = await db.execute(text("""
            select
                to_char(date(uploaded_at), 'DD.MM') as day_label,
                count(*) as uploads_count,
                coalesce(sum(total_rows), 0) as total_rows,
                coalesce(sum(valid_rows), 0) as valid_rows,
                coalesce(sum(invalid_rows), 0) as invalid_rows,
                round(avg(invalid_ratio)::numeric, 2) as avg_invalid_ratio
            from uploads
            where uploaded_at >= now() - interval '7 days'
            group by date(uploaded_at)
            order by date(uploaded_at) asc
        """))
        uploads_daily = [dict(x) for x in uploads_daily_q.mappings().all()]

        latest_import_dict = dict(latest_import) if latest_import else None
        trust_dict = dict(trust) if trust else None

        trust_level = (trust_dict["trust_level"] if trust_dict else "UNKNOWN") or "UNKNOWN"
        pending_anomalies = int(trust_dict["pending_anomalies"]) if trust_dict and trust_dict["pending_anomalies"] is not None else 0
        invalid_ratio = latest_import_dict["invalid_ratio"] if latest_import_dict else None

        attention_items = build_attention_items(
            trust_level=trust_level,
            active_tasks=active_tasks,
            overdue_sla=overdue_sla,
            pending_anomalies=pending_anomalies,
            invalid_ratio=invalid_ratio,
        )

        today_risk = {
            "trust_level": trust_level,
            "overdue_sla": overdue_sla,
            "pending_anomalies": pending_anomalies,
            "active_tasks": active_tasks,
        }

        week_metrics = {
            "uploads_count": sum(int(x["uploads_count"]) for x in uploads_daily) if uploads_daily else 0,
            "total_rows": sum(int(x["total_rows"]) for x in uploads_daily) if uploads_daily else 0,
            "invalid_rows": sum(int(x["invalid_rows"]) for x in uploads_daily) if uploads_daily else 0,
            "avg_invalid_ratio": round(
                sum(float(x["avg_invalid_ratio"] or 0) for x in uploads_daily) / len(uploads_daily), 2
            ) if uploads_daily else 0.0,
        }

        generated_at = datetime.now(timezone.utc).isoformat()

        return {
            "status": "ok",
            "data": {
                "generated_at": generated_at,
                "kpi": {
                    "active_tasks": active_tasks,
                    "overdue_sla": overdue_sla,
                    "invalid_ratio": invalid_ratio,
                    "pending_anomalies": pending_anomalies,
                    "trust_level": trust_level,
                },
                "latest_import": latest_import_dict,
                "trust": trust_dict,
                "top_stores": top_stores,
                "manager_load": manager_load,
                "latest_uploads": latest_uploads,
                "attention_items": attention_items,
                "uploads_daily": uploads_daily,
                "week_metrics": week_metrics,
                "today_risk": today_risk,
                "exec_summary": build_exec_summary(
                    trust_level=trust_level,
                    active_tasks=active_tasks,
                    overdue_sla=overdue_sla,
                    pending_anomalies=pending_anomalies,
                    invalid_ratio=invalid_ratio,
                ),
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
