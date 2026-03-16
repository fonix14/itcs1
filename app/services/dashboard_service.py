from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text


async def _scalar(session, sql: str, params: dict[str, Any] | None = None, default=None):
    try:
        res = await session.execute(text(sql), params or {})
        value = res.scalar()
        return default if value is None else value
    except Exception:
        return default


async def _rows(session, sql: str, params: dict[str, Any] | None = None):
    try:
        res = await session.execute(text(sql), params or {})
        return [dict(x) for x in res.mappings().all()]
    except Exception:
        return []


async def _one_row(session, sql: str, params: dict[str, Any] | None = None):
    try:
        res = await session.execute(text(sql), params or {})
        row = res.mappings().first()
        return dict(row) if row else None
    except Exception:
        return None


def _to_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _trust_level(last_upload_at, invalid_percent: float, open_anomalies: int, critical_open: int) -> str:
    now = datetime.now(timezone.utc)
    parsed_last_upload = _parse_dt(last_upload_at)

    if parsed_last_upload is None:
        return "RED"
    if parsed_last_upload < now - timedelta(hours=48):
        return "RED"
    if critical_open > 0:
        return "RED"
    if invalid_percent >= 20 or open_anomalies > 0:
        return "YELLOW"
    return "GREEN"


async def get_dashboard_metrics(session):
    tasks_total = await _scalar(session, "select count(*) from tasks", default=0)
    uploads_total = await _scalar(session, "select count(*) from uploads", default=0)
    open_anomalies = await _scalar(session, "select count(*) from anomalies where status = 'open'", default=0)
    critical_open = await _scalar(
        session,
        "select count(*) from anomalies where status = 'open' and severity in ('critical', 'CRITICAL')",
        default=0,
    )

    last_upload_at = await _scalar(
        session,
        "select max(coalesce(created_at, uploaded_at)) from uploads",
        default=None,
    )

    metric_row = await _one_row(
        session,
        '''
        select
            coalesce(invalid_ratio, invalid_percent, invalid_pct, 0) as invalid_metric
        from upload_metrics
        order by coalesce(created_at, calculated_at, metric_date) desc
        limit 1
        ''',
    )

    invalid_percent = 0.0
    if metric_row and metric_row.get("invalid_metric") is not None:
        try:
            invalid_percent = float(metric_row["invalid_metric"])
            if invalid_percent <= 1:
                invalid_percent = round(invalid_percent * 100, 2)
            else:
                invalid_percent = round(invalid_percent, 2)
        except Exception:
            invalid_percent = 0.0
    else:
        upload_row = await _one_row(
            session,
            '''
            select
                coalesce(invalid_rows, error_rows, bad_rows, 0) as invalid_rows,
                coalesce(total_rows, rows_total, source_rows, 0) as total_rows
            from uploads
            order by coalesce(created_at, uploaded_at) desc
            limit 1
            ''',
        )
        if upload_row:
            try:
                invalid_rows = float(upload_row.get("invalid_rows") or 0)
                total_rows = float(upload_row.get("total_rows") or 0)
                invalid_percent = round((invalid_rows / total_rows) * 100, 2) if total_rows > 0 else 0.0
            except Exception:
                invalid_percent = 0.0

    trust_level = _trust_level(last_upload_at, invalid_percent, open_anomalies, critical_open)

    return {
        "tasks_total": int(tasks_total or 0),
        "uploads_total": int(uploads_total or 0),
        "open_anomalies": int(open_anomalies or 0),
        "critical_open_anomalies": int(critical_open or 0),
        "last_upload_at": _to_iso(last_upload_at),
        "invalid_percent": invalid_percent,
        "trust_level": trust_level,
    }


async def get_health_metrics(session):
    data = await get_dashboard_metrics(session)
    warnings = []
    if data["last_upload_at"] is None:
        warnings.append("NO_UPLOADS")
    if data["invalid_percent"] >= 20:
        warnings.append("INVALID_RATIO_OVER_20")
    if data["open_anomalies"] > 0:
        warnings.append("OPEN_ANOMALIES_PRESENT")
    if data["critical_open_anomalies"] > 0:
        warnings.append("CRITICAL_ANOMALIES_PRESENT")
    data["warnings"] = warnings
    return data


async def get_sla_metrics(session):
    now = datetime.now(timezone.utc)
    plus_24 = now + timedelta(hours=24)

    overdue = await _scalar(
        session,
        '''
        select count(*)
        from tasks
        where sla is not null
          and status not in ('resolved', 'resolved', 'resolved', 'cancelled')
          and sla < now()
        ''',
        default=0,
    )

    risk_24h = await _scalar(
        session,
        '''
        select count(*)
        from tasks
        where sla is not null
          and status not in ('resolved', 'resolved', 'resolved', 'cancelled')
          and sla >= now()
          and sla < (now() + interval '24 hour')
        ''',
        default=0,
    )

    manager_rows = await _rows(
        session,
        '''
        select
            u.id as user_id,
            coalesce(u.full_name, u.email, u.id::text) as manager_name,
            count(t.id) as active_tasks,
            count(*) filter (
                where t.sla is not null
                  and t.status not in ('resolved', 'resolved', 'resolved', 'cancelled')
                  and t.sla < now()
            ) as overdue_tasks,
            count(*) filter (
                where t.sla is not null
                  and t.status not in ('resolved', 'resolved', 'resolved', 'cancelled')
                  and t.sla >= now()
                  and t.sla < (now() + interval '24 hour')
            ) as risk_24h_tasks
        from users u
        left join stores s on s.assigned_user_id = u.id
        left join tasks t on t.store_id = s.id
        where u.role = 'manager'
        group by u.id, u.full_name, u.email
        order by active_tasks desc, overdue_tasks desc, manager_name asc
        ''',
    )

    manager_workload = []
    for row in manager_rows:
        manager_workload.append(
            {
                "user_id": str(row.get("user_id")),
                "manager_name": row.get("manager_name"),
                "active_tasks": int(row.get("active_tasks") or 0),
                "overdue_tasks": int(row.get("overdue_tasks") or 0),
                "risk_24h_tasks": int(row.get("risk_24h_tasks") or 0),
            }
        )

    return {
        "generated_at": now.isoformat(),
        "overdue_tasks": int(overdue or 0),
        "risk_24h_tasks": int(risk_24h or 0),
        "manager_workload": manager_workload,
    }
