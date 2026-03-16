from __future__ import annotations

from fastapi import HTTPException, Request


def get_current_session_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    display_name = request.session.get("display_name")
    email = request.session.get("email")

    if not user_id or not role:
        raise HTTPException(status_code=401, detail="Требуется вход")

    return {
        "user_id": user_id,
        "role": role,
        "display_name": display_name,
        "email": email,
    }


def require_role(request: Request, *allowed_roles: str) -> dict:
    user = get_current_session_user(request)
    if user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return user
