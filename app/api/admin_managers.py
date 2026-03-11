from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(prefix="/api/admin", tags=["admin_managers"])


class ManagerCreate(BaseModel):
    full_name: str
    email: str | None = None


class ManagerUpdate(BaseModel):
    full_name: str
    email: str | None = None


class StoreAssign(BaseModel):
    assigned_user_id: str | None = None


@router.get("/managers")
async def list_managers(db: AsyncSession = Depends(get_db)):
    try:
        rows = await db.execute(text("""
            select
                u.id,
                coalesce(u.full_name, '—') as full_name,
                coalesce(u.email, '') as email,
                count(s.id) as stores_count
            from users u
            left join stores s on s.assigned_user_id = u.id
            where u.role = 'manager'
            group by u.id, u.full_name, u.email
            order by u.full_name asc nulls last, u.email asc
        """))
        return {"status": "ok", "data": [dict(x) for x in rows.mappings().all()]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/managers")
async def create_manager(payload: ManagerCreate, db: AsyncSession = Depends(get_db)):
    try:
        manager_id = str(uuid4())
        await db.execute(text("""
            insert into users (id, full_name, email, role)
            values (:id, :full_name, :email, 'manager')
        """), {
            "id": manager_id,
            "full_name": payload.full_name,
            "email": payload.email,
        })
        await db.commit()
        return {"status": "ok", "id": manager_id}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.put("/managers/{manager_id}")
async def update_manager(manager_id: str, payload: ManagerUpdate, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("""
            update users
            set full_name = :full_name,
                email = :email
            where id = :id
              and role = 'manager'
        """), {
            "id": manager_id,
            "full_name": payload.full_name,
            "email": payload.email,
        })
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.delete("/managers/{manager_id}")
async def delete_manager(manager_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("""
            update stores
            set assigned_user_id = null
            where assigned_user_id = :id
        """), {"id": manager_id})

        await db.execute(text("""
            delete from users
            where id = :id
              and role = 'manager'
        """), {"id": manager_id})

        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}


@router.get("/stores")
async def list_stores(db: AsyncSession = Depends(get_db)):
    try:
        rows = await db.execute(text("""
            select
                s.id,
                s.store_no,
                s.assigned_user_id,
                coalesce(u.full_name, 'Не назначен') as manager_name
            from stores s
            left join users u on u.id = s.assigned_user_id
            order by s.store_no asc
        """))
        return {"status": "ok", "data": [dict(x) for x in rows.mappings().all()]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.put("/stores/{store_id}/assign")
async def assign_store(store_id: str, payload: StoreAssign, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("""
            update stores
            set assigned_user_id = :assigned_user_id
            where id = :id
        """), {
            "id": store_id,
            "assigned_user_id": payload.assigned_user_id,
        })
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": str(e)}
