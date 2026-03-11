from __future__ import annotations

from typing import Any, Dict


def _s(v: Any, default: str = "—") -> str:
    if v is None:
        return default
    if isinstance(v, str):
        v = v.strip()
        return v if v else default
    return str(v)


def _clip(s: str, limit: int = 900) -> str:
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def render_manager_task_message(task: Dict[str, Any]) -> str:
    portal_task_id = _s(task.get("portal_task_id"))
    created_at = _s(task.get("created_at"))
    store_no = _s(task.get("store_no"))
    sla_date = _s(task.get("sla_date"))
    level4 = _clip(_s(task.get("level4")))
    text = _clip(_s(task.get("text")))
    comments = _clip(_s(task.get("comments")))
    location = _clip(_s(task.get("location")))

    return "\n".join(
        [
            f"🆔 Идентификатор Портала: {portal_task_id}",
            f"🏪 Номер магазина: {store_no}",
            f"📍 Местонахождение: {location}",
            f"🗓️ Дата создания: {created_at}",
            f"⏳ Дата SLA: {sla_date}",
            f"🧩 Уровень 4: {level4}",
            f"📝 Текст обращения: {text}",
            f"💬 Комментарии: {comments}",
        ]
    )
