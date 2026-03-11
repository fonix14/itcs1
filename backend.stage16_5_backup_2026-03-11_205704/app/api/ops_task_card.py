from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db

router=APIRouter(prefix="/api/ops",tags=["ops"])

@router.get("/tasks/{task_id}")
async def task_card(task_id:str,db:AsyncSession=Depends(get_db)):
    task=await db.execute(text("select * from tasks where id=:id"),{"id":task_id})
    comments=await db.execute(text("select * from task_comments where task_id=:id order by created_at desc"),{"id":task_id})
    activity=await db.execute(text("select * from task_activity where task_id=:id order by created_at desc"),{"id":task_id})
    return{
        "task":dict(task.mappings().first() or {}),
        "comments":[dict(x) for x in comments.mappings()],
        "activity":[dict(x) for x in activity.mappings()]
    }