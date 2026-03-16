from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse


PUBLIC_EXACT = {
    "/",
    "/login",
    "/logout",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/docs",
    "/openapi.json",
    "/redoc",
)

DISPATCHER_UI_PREFIXES = (
    "/ui/",
)

MANAGER_UI_PREFIXES = (
    "/m/",
)

DISPATCHER_API_PREFIXES = (
    "/api/admin/",
    "/api/dashboard",
    "/api/director/",
)

MANAGER_OR_DISPATCHER_API_PREFIXES = (
    "/api/mobile/",
)


def _session_user(request: Request) -> dict | None:
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


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def _starts_with_any(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def _json_unauthorized() -> JSONResponse:
    return JSONResponse({"detail": "Login required"}, status_code=401)


def _json_forbidden() -> JSONResponse:
    return JSONResponse({"detail": "Forbidden"}, status_code=403)


async def guard_request(request: Request):
    path = request.url.path

    if _is_public(path):
        return None

    user = _session_user(request)

    if _starts_with_any(path, DISPATCHER_UI_PREFIXES):
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if user["role"] not in {"admin", "dispatcher"}:
            return RedirectResponse(url="/m/tasks", status_code=302)
        return None

    if _starts_with_any(path, MANAGER_UI_PREFIXES):
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if user["role"] not in {"admin", "dispatcher", "manager"}:
            return RedirectResponse(url="/login", status_code=302)
        return None

    if _starts_with_any(path, DISPATCHER_API_PREFIXES):
        if not user:
            return _json_unauthorized()
        if user["role"] not in {"admin", "dispatcher"}:
            return _json_forbidden()
        return None

    if _starts_with_any(path, MANAGER_OR_DISPATCHER_API_PREFIXES):
        if not user:
            return _json_unauthorized()
        if user["role"] not in {"admin", "dispatcher", "manager"}:
            return _json_forbidden()
        return None

    return None
