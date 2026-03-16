from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session

router = APIRouter(prefix="/api/command-center", tags=["command_center"])


DEFAULT_MODULES = [
    {
        "code": "supplier_tasks",
        "name": "Заявки поставщика",
        "description": "Импорт Excel, задачи, SLA и контроль статусов.",
        "route_path": "/ui/tasks",
        "icon": "📋",
    },
    {
        "code": "imports",
        "name": "Импорт Excel",
        "description": "Загрузка файлов и контроль качества данных.",
        "route_path": "/ui/upload",
        "icon": "📥",
    },
    {
        "code": "health",
        "name": "Health & Anomalies",
        "description": "Trust level, аномалии и состояние системы.",
        "route_path": "/ui/dashboard",
        "icon": "🩺",
    },
    {
        "code": "cleaning_journal",
        "name": "Cleaning Journal",
        "description": "Каркас второго модуля для объектов и журналов.",
        "route_path": "/ui/command-center#roadmap",
        "icon": "🧹",
    },
    {
        "code": "ai_assistant",
        "name": "AI Assistant",
        "description": "Управленческие сводки и будущий слой аналитики.",
        "route_path": "/ui/command-center#ai",
        "icon": "🤖",
    },
]

DEFAULT_ACTIONS = [
    {"code": "open_upload", "title": "Загрузить Excel", "route_path": "/ui/upload", "icon": "⬆️"},
    {"code": "open_tasks", "title": "Открыть задачи", "route_path": "/ui/tasks", "icon": "📋"},
    {"code": "open_dashboard", "title": "Открыть dashboard", "route_path": "/ui/dashboard", "icon": "📊"},
    {"code": "open_mobile", "title": "Mobile view", "route_path": "/m/tasks", "icon": "📱"},
    {"code": "open_health", "title": "Health API", "route_path": "/api/dashboard/health", "icon": "🩺"},
]


def _trust_badge(level: str | None) -> dict[str, str]:
    normalized = (level or "UNKNOWN").upper()
    mapping = {
        "GREEN": {"label": "GREEN", "tone": "green"},
        "YELLOW": {"label": "YELLOW", "tone": "yellow"},
        "RED": {"label": "RED", "tone": "red"},
    }
    return mapping.get(normalized, {"label": normalized, "tone": "slate"})


async def _try_fetch_one(session: AsyncSession, sql_list: list[str]) -> dict[str, Any] | None:
    for sql in sql_list:
        try:
            res = await session.execute(text(sql))
            row = res.mappings().first()
            if row:
                return dict(row)
        except Exception:
            continue
    return None


async def _try_fetch_scalar(session: AsyncSession, sql_list: list[str], default: int | float = 0) -> int | float:
    for sql in sql_list:
        try:
            res = await session.execute(text(sql))
            value = res.scalar_one_or_none()
            if value is not None:
                return value
        except Exception:
            continue
    return default


async def _load_latest_upload(session: AsyncSession) -> dict[str, Any] | None:
    return await _try_fetch_one(
        session,
        [
            """
            select id,
                   profile_code,
                   original_filename as filename,
                   uploaded_at,
                   invalid_ratio
            from uploads
            order by uploaded_at desc
            limit 1
            """,
            """
            select id,
                   profile_code,
                   filename,
                   uploaded_at,
                   invalid_ratio
            from uploads
            order by uploaded_at desc
            limit 1
            """,
            """
            select id,
                   profile_code,
                   file_name as filename,
                   created_at as uploaded_at,
                   invalid_ratio
            from uploads
            order by created_at desc
            limit 1
            """,
        ],
    )


async def _load_trust(session: AsyncSession) -> dict[str, Any] | None:
    return await _try_fetch_one(
        session,
        [
            """
            select trust_level,
                   calculated_at,
                   no_import_duration_hours,
                   pending_anomalies
            from health_state
            order by calculated_at desc
            limit 1
            """,
            """
            select trust_level,
                   calculated_at,
                   no_import_hours as no_import_duration_hours,
                   pending_anomalies
            from health_state
            order by calculated_at desc
            limit 1
            """,
        ],
    )


async def _load_modules(session: AsyncSession) -> list[dict[str, Any]]:
    try:
        res = await session.execute(
            text(
                """
                select code, name, description, route_path, icon
                from platform_modules
                where is_enabled = true
                order by sort_order asc, id asc
                """
            )
        )
        rows = [dict(x) for x in res.mappings().all()]
        return rows or DEFAULT_MODULES
    except Exception:
        return DEFAULT_MODULES


async def _load_quick_actions(session: AsyncSession) -> list[dict[str, Any]]:
    try:
        res = await session.execute(
            text(
                """
                select code, title, route_path, icon
                from platform_quick_actions
                where is_enabled = true
                order by sort_order asc, id asc
                """
            )
        )
        rows = [dict(x) for x in res.mappings().all()]
        return rows or DEFAULT_ACTIONS
    except Exception:
        return DEFAULT_ACTIONS


async def _build_summary(session: AsyncSession, trust_level: str | None, invalid_ratio: float | None, overdue_sla: int) -> str:
    try:
        if trust_level == "RED":
            head = "Система находится в красной зоне доверия к данным."
        elif trust_level == "YELLOW":
            head = "Система требует внимания: trust level в жёлтой зоне."
        elif trust_level == "GREEN":
            head = "Система работает штатно, критичных сигналов мало."
        else:
            head = "Trust level пока не определён, нужен контроль последнего импорта."

        parts = [head]
        if invalid_ratio is not None:
            parts.append(f"Доля невалидных строк последнего импорта: {float(invalid_ratio):.1f}%.")
        if overdue_sla > 0:
            parts.append(f"Просроченных задач по SLA: {overdue_sla}.")

        anomaly_count = await _try_fetch_scalar(
            session,
            [
                "select count(*) from anomalies where status in ('pending','open','new')",
                "select count(*) from anomalies",
            ],
            0,
        )
        if anomaly_count:
            parts.append(f"Открытых аномалий: {int(anomaly_count)}.")

        return " ".join(parts)
    except Exception:
        return "Командный центр доступен. Проверьте свежесть импорта, доверие к данным и просрочки SLA."


@router.get("/overview")
async def command_center_overview(session: AsyncSession = Depends(db_session)):
    try:
        latest_upload = await _load_latest_upload(session)
        trust = await _load_trust(session)

        active_tasks = int(
            await _try_fetch_scalar(
                session,
                [
                    """
                    select count(*)
                    from tasks
                    where coalesce(status, '') not in ('resolved', 'resolved', 'cancelled', 'resolved')
                    """,
                    "select count(*) from tasks",
                ],
                0,
            )
        )

        overdue_sla = int(
            await _try_fetch_scalar(
                session,
                [
                    """
                    select count(*)
                    from tasks
                    where sla_due_at is not null
                      and sla_due_at < now()
                      and coalesce(status, '') not in ('resolved', 'resolved', 'cancelled', 'resolved')
                    """,
                    """
                    select count(*)
                    from tasks
                    where sla is not null
                      and sla < now()
                      and coalesce(status, '') not in ('resolved', 'resolved', 'cancelled', 'resolved')
                    """,
                ],
                0,
            )
        )

        pending_anomalies = int(
            await _try_fetch_scalar(
                session,
                [
                    "select count(*) from anomalies where status in ('pending','open','new')",
                    "select count(*) from anomalies",
                ],
                0,
            )
        )

        modules = await _load_modules(session)
        quick_actions = await _load_quick_actions(session)

        invalid_ratio = None
        if latest_upload and latest_upload.get("invalid_ratio") is not None:
            invalid_ratio = float(latest_upload["invalid_ratio"])

        trust_level = None
        if trust:
            trust_level = trust.get("trust_level")
            trust["badge"] = _trust_badge(trust_level)

        summary_text = await _build_summary(session, trust_level, invalid_ratio, overdue_sla)

        return {
            "status": "ok",
            "data": {
                "trust": trust,
                "latest_upload": latest_upload,
                "kpi": {
                    "active_tasks": active_tasks,
                    "overdue_sla": overdue_sla,
                    "pending_anomalies": pending_anomalies,
                    "invalid_ratio": invalid_ratio,
                },
                "quick_actions": quick_actions,
                "modules": modules,
                "summary": {
                    "title": "Краткая управленческая сводка",
                    "text": summary_text,
                },
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
