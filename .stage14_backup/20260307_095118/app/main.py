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

from app.ui_dashboard import router as ui_dashboard_router
from app.ui_tasks import router as ui_tasks_router
from app.ui_mobile_portal import router as ui_mobile_portal_router

app = FastAPI(title="ITCS Stage12 Fixed")
app.mount("/static", StaticFiles(directory="/app/app/static"), name="static")

# Base UI
app.include_router(ui_router)
app.include_router(ui_ops_router)

# Import
app.include_router(tasks_upload_router)
app.include_router(portal_l4_router)

# Ops
app.include_router(ops_tasks_ws)
app.include_router(ops_task_card)
app.include_router(ops_actions)
app.include_router(dashboard_router)

# UI
app.include_router(ui_dashboard_router)
app.include_router(tasks_ui_router)
app.include_router(ui_tasks_router)

# Mobile portal + API
app.include_router(ui_mobile_portal_router)
app.include_router(mobile_manager_router)

@app.get("/")
async def root():
    return {"status": "ok"}
