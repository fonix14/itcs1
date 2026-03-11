from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["ui-mobile-portal"])


@router.get("/m/tasks", response_class=HTMLResponse)
async def mobile_tasks(request: Request):
    return templates.TemplateResponse(
        "mobile_tasks_portal.html",
        {"request": request, "page_title": "ITCS Mobile Portal"},
    )


@router.get("/m/task/{task_id:str}", response_class=HTMLResponse)
async def mobile_task_card(request: Request, task_id: str):
    return templates.TemplateResponse(
        "mobile_task_portal.html",
        {"request": request, "page_title": f"ITCS Task {task_id}", "task_id": task_id},
    )


@router.get("/manifest.webmanifest")
async def manifest():
    return FileResponse(
        str(BASE_DIR / "static" / "manifest.webmanifest"),
        media_type="application/manifest+json",
    )


@router.get("/sw.js")
async def service_worker():
    return FileResponse(
        str(BASE_DIR / "static" / "sw.js"),
        media_type="application/javascript",
    )
