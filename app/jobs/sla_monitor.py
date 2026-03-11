import sys
import asyncio
from datetime import datetime, timezone

# чтобы python внутри контейнера видел пакет /app
sys.path.append("/app")

from sqlalchemy import text
from app.db import get_db


def fmt_dt(value):
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def overdue_hours(sla_due_at):
    if not sla_due_at:
        return "—"
    now = datetime.now(timezone.utc)
    if sla_due_at.tzinfo is None:
        sla_due_at = sla_due_at.replace(tzinfo=timezone.utc)
    diff = now - sla_due_at
    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)
    if hours < 0:
        return "0ч 0м"
    return f"{hours}ч {minutes}м"


async def run():
    async for db in get_db():

        q = text("""
        SELECT
            t.id,
            t.portal_task_id,
            t.sla_due_at,
            t.payload
        FROM tasks t
        WHERE t.status = 'open'
          AND t.sla_due_at IS NOT NULL
          AND t.sla_due_at < now()
        """)

        res = await db.execute(q)
        tasks = res.mappings().all()

        for t in tasks:

            check = await db.execute(text("""
            SELECT 1
            FROM task_activity
            WHERE task_id = :task_id
              AND event_type = 'sla_overdue'
            LIMIT 1
            """), {"task_id": t["id"]})

            if check.first():
                continue

            payload = t["payload"] or {}

            portal_task_id = str(t["portal_task_id"])
            sla_due_at = t["sla_due_at"]
            sla_text = fmt_dt(sla_due_at)
            overdue_text = overdue_hours(sla_due_at)

            store_no = payload.get("store_no", "—")
            location = payload.get("location", "—")
            text_body = payload.get("text", "—")
            level4 = payload.get("level4", "—")

            message_text = (
                "⚠ ПРОСРОЧЕН SLA\n\n"
                f"Заявка: {portal_task_id}\n"
                f"Магазин: {store_no}\n"
                f"Уровень 4: {level4}\n"
                f"Срок SLA: {sla_text}\n"
                f"Просрочка: {overdue_text}\n"
                f"Адрес: {location}\n\n"
                f"Текст: {text_body}\n\n"
                "Требуется реакция менеджера."
            )

            message_html = (
                "<b>⚠ ПРОСРОЧЕН SLA</b><br><br>"
                f"<b>Заявка:</b> {portal_task_id}<br>"
                f"<b>Магазин:</b> {store_no}<br>"
                f"<b>Уровень 4:</b> {level4}<br>"
                f"<b>Срок SLA:</b> {sla_text}<br>"
                f"<b>Просрочка:</b> {overdue_text}<br>"
                f"<b>Адрес:</b> {location}<br><br>"
                f"<b>Текст:</b> {text_body}<br><br>"
                "Требуется реакция менеджера."
            )

            await db.execute(text("""
            INSERT INTO task_activity
                (task_id, event_type, created_at)
            VALUES
                (:task_id, 'sla_overdue', now())
            """), {"task_id": t["id"]})

            await db.execute(text("""
            INSERT INTO notification_outbox
                (
                    channel,
                    recipient_address,
                    template,
                    payload,
                    status,
                    attempts,
                    next_retry_at,
                    dedupe_key,
                    created_at
                )
            VALUES
                (
                    'matrix',
                    '',
                    'sla_overdue',
                    json_build_object(
                        'portal_task_id', CAST(:portal_task_id AS text),
                        'sla_due_at', CAST(:sla_due_at AS text),
                        'store_no', CAST(:store_no AS text),
                        'location', CAST(:location AS text),
                        'level4', CAST(:level4 AS text),
                        'text', CAST(:msg_text AS text),
                        'html', CAST(:msg_html AS text)
                    ),
                    'queued',
                    0,
                    now(),
                    :dedupe_key,
                    now()
                )
            ON CONFLICT (dedupe_key) DO NOTHING
            """), {
                "portal_task_id": portal_task_id,
                "sla_due_at": sla_text,
                "store_no": str(store_no),
                "location": str(location),
                "level4": str(level4),
                "msg_text": message_text,
                "msg_html": message_html,
                "dedupe_key": f"sla_overdue:{t['id']}",
            })

        await db.commit()


if __name__ == "__main__":
    asyncio.run(run())
