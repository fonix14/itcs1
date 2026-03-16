from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import Depends, Form, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db


PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str) -> str:
    if not password:
        raise ValueError("empty password")
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return base64.b64encode(dk).decode("utf-8")


def make_password_pair(password: str) -> tuple[str, str]:
    salt = secrets.token_urlsafe(24)
    return salt, hash_password(password, salt)


def verify_password(password: str, salt: Optional[str], password_hash: Optional[str]) -> bool:
    try:
        if not password or not salt or not password_hash:
            return False
        calc = hash_password(password, salt)
        return hmac.compare_digest(calc, password_hash)
    except Exception:
        return False


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> dict | None:
    try:
        res = await session.execute(
            text(
                """
                select
                    id::text as id,
                    email,
                    full_name,
                    role,
                    is_active,
                    password_salt,
                    password_hash
                from users
                where lower(email) = lower(:email)
                limit 1
                """
            ),
            {"email": email.strip()},
        )
        row = res.mappings().first()
        if not row:
            return None

        user = dict(row)
        if not user.get("is_active", True):
            return None

        ok = verify_password(
            password=password,
            salt=user.get("password_salt"),
            password_hash=user.get("password_hash"),
        )
        if not ok:
            return None

        return {
            "user_id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": str(user["role"]).strip().lower(),
        }
    except Exception:
        return None


def login_form_email(email: str = Form(...)) -> str:
    return email.strip()


def login_form_password(password: str = Form(...)) -> str:
    return password


def get_session_actor(request: Request) -> tuple[str | None, str | None]:
    try:
        session = request.session or {}
        user_id = session.get("user_id")
        role = session.get("role")
        if user_id and role:
            return str(user_id), str(role).strip().lower()
        return None, None
    except Exception:
        return None, None


async def get_actor_from_session_or_header(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> tuple[str | None, str | None]:
    session_user_id, session_role = get_session_actor(request)
    if session_user_id and session_role:
        return session_user_id, session_role

    if x_user_id and x_user_role:
        return str(x_user_id), str(x_user_role).strip().lower()

    return None, None


async def require_login(
    request: Request,
    actor: tuple[str | None, str | None] = Depends(get_actor_from_session_or_header),
) -> dict:
    user_id, role = actor
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )

    return {
        "user_id": user_id,
        "role": role,
        "full_name": request.session.get("full_name"),
        "email": request.session.get("email"),
    }


async def require_dispatcher(user: dict = Depends(require_login)) -> dict:
    if user["role"] not in {"dispatcher", "admin"}:
        raise HTTPException(status_code=403, detail="Dispatcher access required")
    return user


async def require_manager_or_dispatcher(user: dict = Depends(require_login)) -> dict:
    if user["role"] not in {"manager", "dispatcher", "admin"}:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


async def require_manager_only(user: dict = Depends(require_login)) -> dict:
    if user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Manager access required")
    return user
