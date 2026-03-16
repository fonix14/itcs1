from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_manager import hash_password
from app.authz import require_role
from app.db import get_db

router = APIRouter(prefix="/api/admin", tags=["admin_users"])


class AdminUserCreate(BaseModel):
    full_name: str
    email: str
    role: str
    password: str


class AdminUserUpdate(BaseModel):
    full_name: str
    email: str
    role: str
    is_active: bool


class AdminPasswordSet(BaseModel):
    password: str


ALLOWED_ROLES = {"admin", "dispatcher", "manager"}


@router.get("/users")
async def admin_list_users(request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    rows = await db.execute(text("""
        select
            id::text as id,
            coalesce(full_name, '') as full_name,
            coalesce(display_name, '') as display_name,
            coalesce(email, '') as email,
            role::text as role,
            is_active,
            last_login_at,
            password_changed_at
        from users
        order by
            case role::text
                when 'admin' then 1
                when 'dispatcher' then 2
                when 'manager' then 3
                else 9
            end,
            full_name asc,
            email asc
    """))
    return {"status": "ok", "data": [dict(x) for x in rows.mappings().all()]}


@router.post("/users")
async def admin_create_user(payload: AdminUserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    role = payload.role.strip()
    if role not in ALLOWED_ROLES:
        return {"status": "error", "error": "Недопустимая роль"}

    full_name = payload.full_name.strip()
    email = payload.email.strip().lower()
    password = payload.password.strip()

    if not full_name or not email or not password:
        return {"status": "error", "error": "Все поля обязательны"}

    password_hash = hash_password(password)

    try:
        await db.execute(text("""
            insert into users (
                id,
                full_name,
                display_name,
                email,
                role,
                is_active,
                password_hash,
                password_changed_at
            )
            values (
                gen_random_uuid(),
                :full_name,
                :display_name,
                :email,
                CAST(:role AS user_role),
                true,
                :password_hash,
                now()
            )
        """), {
            "full_name": full_name,
            "display_name": full_name,
            "email": email,
            "role": role,
            "password_hash": password_hash,
        })
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.put("/users/{user_id}")
async def admin_update_user(user_id: str, payload: AdminUserUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    role = payload.role.strip()
    if role not in ALLOWED_ROLES:
        return {"status": "error", "error": "Недопустимая роль"}

    try:
        await db.execute(text("""
            update users
            set
                full_name = :full_name,
                display_name = :display_name,
                email = :email,
                role = CAST(:role AS user_role),
                is_active = :is_active
            where id::text = :user_id
        """), {
            "user_id": user_id,
            "full_name": payload.full_name.strip(),
            "display_name": payload.full_name.strip(),
            "email": payload.email.strip().lower(),
            "role": role,
            "is_active": payload.is_active,
        })
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.post("/users/{user_id}/set-password")
async def admin_set_password(user_id: str, payload: AdminPasswordSet, request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    password = payload.password.strip()
    if not password:
        return {"status": "error", "error": "Пароль пустой"}

    try:
        await db.execute(text("""
            update users
            set
                password_hash = :password_hash,
                password_changed_at = now()
            where id::text = :user_id
        """), {
            "user_id": user_id,
            "password_hash": hash_password(password),
        })
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.post("/users/{user_id}/deactivate")
async def admin_deactivate_user(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    try:
        await db.execute(text("""
            update users
            set is_active = false
            where id::text = :user_id
        """), {"user_id": user_id})
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    try:
        ref = (
            await db.execute(text("""
                select exists(
                    select 1 from stores where assigned_user_id::text = :user_id
                ) as has_store_refs
            """), {"user_id": user_id})
        ).mappings().first()

        if ref and ref["has_store_refs"]:
            return {"status": "error", "error": "Пользователь связан с магазинами. Используй деактивацию."}

        await db.execute(text("""
            delete from users
            where id::text = :user_id
        """), {"user_id": user_id})
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}
