from __future__ import annotations

from typing import Any, Dict


def _s(v: Any, default: str = "—") -> str:
    if v is None:
        return default
    s = str(v).strip()
    return s or default


def render_push_payload(template: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    manager_user_id = payload.get("manager_user_id")
    task_id = payload.get("task_id")
    upload_id = payload.get("upload_id")
    portal_task_id = payload.get("portal_task_id")
    store_no = payload.get("store_no")

    if template in ("manager_task_new", "manager_task") or payload.get("kind") == "new_task":
        title = f"Новая заявка { _s(store_no, '') }".strip()
        body = f"Portal: {_s(portal_task_id)} · Магазин: {_s(store_no)}"
        url = f"/m/task/{task_id}" if task_id else "/m/tasks"
        return {"title": title, "body": body, "url": url, "tag": f"task:{task_id or portal_task_id or 'new'}", "manager_user_id": manager_user_id}

    if template == "manager_digest" or payload.get("kind") == "digest":
        title = "Импорт завершён"
        body = payload.get("text") or f"Upload {upload_id}"
        return {"title": title, "body": body[:180], "url": "/m/tasks", "tag": f"digest:{upload_id or 'latest'}", "manager_user_id": manager_user_id}

    if template == "risk_reminder":
        return {"title": "Требуется внимание", "body": _s(payload.get("text")), "url": "/m/tasks", "tag": "risk-reminder", "manager_user_id": manager_user_id}

    return {"title": "ITCS", "body": _s(payload.get("text"), "Новое уведомление"), "url": "/m/tasks", "tag": f"generic:{template or 'notification'}", "manager_user_id": manager_user_id}
