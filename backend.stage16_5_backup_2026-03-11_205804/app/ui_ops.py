from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["ui-ops"])
templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/ui/tasks/{task_id}", response_class=HTMLResponse)
async def ui_task_card(task_id: str, request: Request):
    return templates.TemplateResponse(
        "task_card.html",
        {"request": request, "task_id": task_id},
    )
