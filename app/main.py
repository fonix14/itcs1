from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.ui import router as ui_router
from app.ui_ops import router as ui_ops_router

from app.api.tasks_uploads import router as tasks_upload_router
from app.api.portal_l4_uploads import router as portal_l4_router
from app.api.ops_tasks_workspace import router as ops_tasks_ws
from app.api.ops_task_card import router as ops_task_card
from app.api.ops_actions import router as ops_actions
from app.api.dashboard import router as dashboard_router
from app.api.tasks_ui import router as tasks_ui_router
from app.api.mobile_manager import router as mobile_manager_router
from app.api.mobile_task_workflow import router as mobile_task_workflow_router
from app.api.director_landing import router as director_landing_router
from app.api.admin_managers import router as admin_managers_router
from app.api.command_center import router as command_center_router
from app.api.director_dashboard import router as director_dashboard_router
from app.api.health_recompute import router as health_recompute_router

from app.ui_admin_managers import router as ui_admin_managers_router
from app.ui_director_landing import router as ui_director_landing_router
from app.ui_dashboard import router as ui_dashboard_router
from app.ui_tasks import router as ui_tasks_router
from app.ui_mobile_portal import router as ui_mobile_portal_router
from app.ui_command_center import router as ui_command_center_router
from app.ui_director_dashboard import router as ui_director_dashboard_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ITCS MVP Stage4")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(admin_managers_router)
app.include_router(tasks_upload_router)
app.include_router(portal_l4_router)
app.include_router(ops_tasks_ws)
app.include_router(ops_task_card)
app.include_router(ops_actions)
app.include_router(dashboard_router)
app.include_router(tasks_ui_router)
app.include_router(mobile_manager_router)
app.include_router(mobile_task_workflow_router)
app.include_router(director_landing_router)
app.include_router(command_center_router)
app.include_router(director_dashboard_router)
app.include_router(health_recompute_router)

app.include_router(ui_router)
app.include_router(ui_director_landing_router)
app.include_router(ui_director_dashboard_router)
app.include_router(ui_dashboard_router)
app.include_router(ui_tasks_router)
app.include_router(ui_admin_managers_router)
app.include_router(ui_mobile_portal_router)
app.include_router(ui_ops_router)
app.include_router(ui_command_center_router)

@app.get("/")
async def root():
    return {"status": "ok"}
