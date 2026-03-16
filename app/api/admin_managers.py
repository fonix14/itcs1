from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_dispatcher, make_password_pair
from app.db import db_session

router = APIRouter(
    prefix="/api/admin",
    tags=["admin_managers"],
    dependencies=[Depends(require_dispatcher)],
)


class ManagerCreateIn(BaseModel):
    full_name: str
    email: str | None = None


class ManagerUpdateIn(BaseModel):
    full_name: str
    email: str | None = None
    is_active: bool = True


class ReassignStoreIn(BaseModel):
    assigned_user_id: str | None = None


class ManagerPasswordIn(BaseModel):
    password: str


@router.get("/managers")
async def list_managers(session: AsyncSession = Depends(db_session)):
    try:
        result = await session.execute(
            text(
                """
                select
                    u.id::text as id,
                    u.full_name,
                    u.email,
                    u.role,
                    u.is_active,
                    coalesce(count(s.id), 0) as stores_count
                from users u
                left join stores s on s.assigned_user_id = u.id
                where u.role = 'manager'
                group by u.id, u.full_name, u.email, u.role, u.is_active
                order by u.full_name asc
                """
            )
        )
        return {"status": "ok", "data": [dict(r) for r in result.mappings().all()]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/managers")
async def create_manager(payload: ManagerCreateIn, session: AsyncSession = Depends(db_session)):
    try:
        full_name = (payload.full_name or "").strip()
        email = ((payload.email or "").strip().lower()) or None

        if not full_name:
            raise HTTPException(status_code=400, detail="ФИО обязательно")

        if email:
            exists = await session.execute(
                text("select 1 from users where lower(email) = lower(:email) limit 1"),
                {"email": email},
            )
            if exists.scalar():
                raise HTTPException(status_code=409, detail="Email already exists")

        manager_id = str(uuid4())

        await session.execute(
            text(
                """
                insert into users (id, full_name, email, role, is_active)
                values (cast(:id as uuid), :full_name, :email, 'manager', true)
                """
            ),
            {
                "id": manager_id,
                "full_name": full_name,
                "email": email,
            },
        )
        await session.commit()

        return {
            "status": "ok",
            "data": {
                "id": manager_id,
                "full_name": full_name,
                "email": email,
                "role": "manager",
                "is_active": True,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}


@router.put("/managers/{manager_id}")
async def update_manager(
    manager_id: str,
    payload: ManagerUpdateIn,
    session: AsyncSession = Depends(db_session),
):
    try:
        full_name = (payload.full_name or "").strip()
        email = ((payload.email or "").strip().lower()) or None

        if not full_name:
            raise HTTPException(status_code=400, detail="ФИО обязательно")

        if email:
            exists = await session.execute(
                text(
                    """
                    select 1
                    from users
                    where lower(email) = lower(:email)
                      and id <> cast(:id as uuid)
                    limit 1
                    """
                ),
                {"email": email, "id": manager_id},
            )
            if exists.scalar():
                raise HTTPException(status_code=409, detail="Email already exists")

        await session.execute(
            text(
                """
                update users
                set
                    full_name = :full_name,
                    email = :email,
                    is_active = :is_active
                where id = cast(:id as uuid)
                  and role = 'manager'
                """
            ),
            {
                "id": manager_id,
                "full_name": full_name,
                "email": email,
                "is_active": payload.is_active,
            },
        )
        await session.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}


@router.put("/managers/{manager_id}/password")
async def update_manager_password(
    manager_id: str,
    payload: ManagerPasswordIn,
    session: AsyncSession = Depends(db_session),
):
    try:
        password = (payload.password or "").strip()
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")

        salt, password_hash = make_password_pair(password)

        result = await session.execute(
            text(
                """
                update users
                set
                    password_salt = :salt,
                    password_hash = :password_hash
                where id = cast(:id as uuid)
                  and role = 'manager'
                """
            ),
            {
                "id": manager_id,
                "salt": salt,
                "password_hash": password_hash,
            },
        )

        if not result.rowcount:
            raise HTTPException(status_code=404, detail="Менеджер не найден")

        await session.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}


@router.delete("/managers/{manager_id}")
async def delete_manager(manager_id: str, session: AsyncSession = Depends(db_session)):
    try:
        await session.execute(
            text(
                """
                update stores
                set assigned_user_id = null
                where assigned_user_id = cast(:id as uuid)
                """
            ),
            {"id": manager_id},
        )

        await session.execute(
            text(
                """
                delete from users
                where id = cast(:id as uuid)
                  and role = 'manager'
                """
            ),
            {"id": manager_id},
        )
        await session.commit()
        return {"status": "ok"}
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}


@router.get("/stores")
async def list_stores(session: AsyncSession = Depends(db_session)):
    try:
        result = await session.execute(
            text(
                """
                select
                    s.id::text as id,
                    s.store_no,
                    s.name,
                    s.address,
                    s.assigned_user_id::text as assigned_user_id,
                    u.full_name as assigned_user_name,
                    u.full_name as manager_name,
                    u.email as assigned_user_email,
                    u.email as manager_email
                from stores s
                left join users u on u.id = s.assigned_user_id
                order by s.store_no asc
                """
            )
        )
        return {"status": "ok", "data": [dict(r) for r in result.mappings().all()]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.put("/stores/{store_id}/assign")
async def assign_store(
    store_id: str,
    payload: ReassignStoreIn,
    session: AsyncSession = Depends(db_session),
):
    try:
        assigned_user_id = payload.assigned_user_id

        if assigned_user_id:
            manager_check = await session.execute(
                text(
                    """
                    select 1
                    from users
                    where id = cast(:id as uuid)
                      and role = 'manager'
                    limit 1
                    """
                ),
                {"id": assigned_user_id},
            )
            if not manager_check.scalar():
                raise HTTPException(status_code=404, detail="Manager not found")

        await session.execute(
            text(
                """
                update stores
                set assigned_user_id = cast(:assigned_user_id as uuid)
                where id = cast(:store_id as uuid)
                """
            ),
            {
                "store_id": store_id,
                "assigned_user_id": assigned_user_id,
            },
        )
        await session.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}
