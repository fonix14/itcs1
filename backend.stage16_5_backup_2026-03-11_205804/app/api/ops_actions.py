from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db

router=APIRouter(prefix="/api/ops",tags=["ops"])

@router.post("/tasks/{task_id}/ack")
async def ack(task_id:str,db:AsyncSession=Depends(get_db)):
    await db.execute(text("""
    insert into task_internal_state(task_id,ack_at)
    values(:id,now())
    on conflict(task_id) do update set ack_at=now()
    """),{"id":task_id})
    await db.commit()
    return{"status":"ok"}

@router.post("/tasks/{task_id}/visit")
async def visit(task_id:str,planned:str,db:AsyncSession=Depends(get_db)):
    await db.execute(text("""
    insert into task_internal_state(task_id,planned_visit_at)
    values(:id,:p)
    on conflict(task_id) do update set planned_visit_at=:p
    """),{"id":task_id,"p":planned})
    await db.commit()
    return{"status":"ok"}

@router.post("/tasks/{task_id}/comments")
async def comment(task_id:str,body:str,db:AsyncSession=Depends(get_db)):
    await db.execute(text("""
    insert into task_comments(task_id,body)
    values(:id,:b)
    """),{"id":task_id,"b":body})
    await db.commit()
    return{"status":"ok"}