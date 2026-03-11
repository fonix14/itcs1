from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(prefix="/api/director", tags=["director_landing"])


@router.get("/landing")
async def director_landing(db: AsyncSession = Depends(get_db)):
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
                file_name,
                profile_id,
                uploaded_at,
                invalid_ratio
            from uploads
            order by uploaded_at desc
            limit 1
        """))
        latest_import = latest_import_q.mappings().first()

        trust_q = await db.execute(text("""
            select trust_level, pending_anomalies, calculated_at
            from health_state
            order by calculated_at desc
            limit 1
        """))
        trust = trust_q.mappings().first()

        trust_level = (trust["trust_level"] if trust else "UNKNOWN") or "UNKNOWN"
        pending_anomalies = int(trust["pending_anomalies"]) if trust and trust["pending_anomalies"] is not None else 0

        modules = [
            {
                "code": "x5_tasks",
                "title": "Контроль заявок X5",
                "status": "active",
                "description": "Импорт Excel, контроль задач, SLA, аномалии и оперативный контроль диспетчера.",
                "route": "/ui/director/dashboard",
                "tag": "В работе"
            },
            {
                "code": "command_center",
                "title": "Операционный командный центр",
                "status": "active",
                "description": "Единая точка входа для ключевых действий, модулей и управленческого обзора.",
                "route": "/ui/director",
                "tag": "Главный экран"
            },
            {
                "code": "cleaning_journal",
                "title": "Журнал клининговых объектов",
                "status": "planned",
                "description": "Объекты, площади, выходы, невыходы, журнал событий и контроль обслуживания.",
                "route": "#",
                "tag": "Следующий этап"
            },
            {
                "code": "analytics",
                "title": "Управленческая аналитика",
                "status": "planned",
                "description": "Сводки по объектам, динамика загрузок, риски по магазинам и контроль деградации.",
                "route": "/ui/director/dashboard",
                "tag": "Расширение"
            },
            {
                "code": "ai_layer",
                "title": "AI-слой платформы",
                "status": "planned",
                "description": "Управленческие сводки, объяснение аномалий, поиск проблемных зон и будущий assistant layer.",
                "route": "#",
                "tag": "Будущий слой"
            },
        ]

        roadmap = [
            {"stage": "Stage 15A", "title": "Command Center", "status": "done"},
            {"stage": "Stage 15B", "title": "Executive Dashboard", "status": "done"},
            {"stage": "Stage 15C", "title": "Mini Analytics", "status": "done"},
            {"stage": "Stage 15D", "title": "Director Landing", "status": "done"},
            {"stage": "Stage 15E", "title": "Unified Navigation", "status": "done"},
            {"stage": "Stage 16", "title": "Cleaning Module Skeleton", "status": "next"},
        ]

        return {
            "status": "ok",
            "data": {
                "hero": {
                    "title": "Операционный командный центр",
                    "subtitle": "Единая точка входа для контроля задач, SLA, аномалий, управленческого обзора и будущих модулей компании.",
                },
                "kpi": {
                    "active_tasks": active_tasks,
                    "overdue_sla": overdue_sla,
                    "pending_anomalies": pending_anomalies,
                    "trust_level": trust_level,
                    "last_import_at": latest_import["uploaded_at"] if latest_import else None,
                    "invalid_ratio": latest_import["invalid_ratio"] if latest_import else None,
                },
                "latest_import": dict(latest_import) if latest_import else None,
                "modules": modules,
                "roadmap": roadmap,
                "platform_value": [
                    "Один портал вместо разрозненных Excel и ручных маршрутов.",
                    "Контроль рисков и SLA в едином интерфейсе.",
                    "Управляемое развитие платформы без усложнения MVP.",
                    "Основа для будущего AI-слоя и внутренней аналитики.",
                ],
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
