from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse


def get_session_user(request: Request) -> dict | None:
    try:
        session = request.session or {}
        user_id = session.get("user_id")
        role = (session.get("role") or "").strip().lower()
        if not user_id or role not in {"admin", "dispatcher", "manager"}:
            return None
        return {
            "user_id": str(user_id),
            "role": role,
            "email": session.get("email"),
            "full_name": session.get("full_name"),
        }
    except Exception:
        return None


def require_ui_login(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return user


def require_ui_dispatcher(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user["role"] not in {"admin", "dispatcher"}:
        return RedirectResponse(url="/m/tasks", status_code=302)
    return user


def require_ui_manager_or_dispatcher(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user["role"] not in {"admin", "dispatcher", "manager"}:
        return RedirectResponse(url="/login", status_code=302)
    return user
