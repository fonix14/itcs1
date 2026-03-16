from pathlib import Path
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth_ui import get_session_user
from app.ui import router as ui_router
from app.ui_ops import router as ui_ops_router

from app.api.tasks_uploads import router as tasks_upload_router
from app.api.portal_l4_uploads import router as portal_l4_router
from app.api.ops_tasks_workspace import router as ops_tasks_ws
from app.api.ops_task_card import router as ops_task_card
from app.api.ops_actions import router as ops_actions
from app.api.dashboard import router as dashboard_router
from app.api.tasks_ui import router as tasks_ui_router
from app.api.task_single import router as api_task_single_router
from app.api.mobile_manager import router as mobile_manager_router
from app.api.mobile_task_workflow import router as mobile_task_workflow_router
from app.api.director_landing import router as director_landing_router
from app.api.admin_managers import router as admin_managers_router
from app.api.admin_profile import router as admin_profile_router
from app.api.admin_server_overview import router as admin_server_overview_router
from app.api.command_center import router as command_center_router
from app.api.director_dashboard import router as director_dashboard_router
from app.api.health_recompute import router as health_recompute_router

from app.ui_admin_managers import router as ui_admin_managers_router
from app.ui_admin_profile import router as ui_admin_profile_router
from app.ui_director_landing import router as ui_director_landing_router
from app.ui_dashboard import router as ui_dashboard_router
from app.ui_tasks import router as ui_tasks_router
from app.ui_task_page import router as ui_task_page_router
from app.ui_mobile_portal import router as ui_mobile_portal_router
from app.ui_command_center import router as ui_command_center_router
from app.ui_director_dashboard import router as ui_director_dashboard_router
from app.ui_login import router as ui_login_router

from app.ui_task_page import router as ui_task_page

from app.bootstrap import ensure_bootstrap_admin
from app.db import SessionLocal

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ITCS MVP Stage4")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me-itcs-session-secret"),
    session_cookie="itcs_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 12,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(ui_login_router)

app.include_router(admin_managers_router)
app.include_router(admin_profile_router)
app.include_router(admin_server_overview_router)
app.include_router(tasks_upload_router)
app.include_router(portal_l4_router)
app.include_router(ops_tasks_ws)
app.include_router(ops_task_card)
app.include_router(ops_actions)
app.include_router(dashboard_router)
app.include_router(tasks_ui_router)
app.include_router(api_task_single_router)
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
app.include_router(ui_task_page_router)
app.include_router(ui_admin_managers_router)
app.include_router(ui_admin_profile_router)
app.include_router(ui_mobile_portal_router)
app.include_router(ui_ops_router)
app.include_router(ui_command_center_router)

app.include_router(ui_task_page)

def _redirect_by_role(role: str | None) -> str:
    role = (role or "").strip().lower()
    if role in {"dispatcher", "admin"}:
        return "/ui/dashboard"
    if role == "manager":
        return "/m/tasks"
    return "/login"


@app.on_event("startup")
async def bootstrap_admin_on_startup():
    try:
        async with SessionLocal() as session:
            await ensure_bootstrap_admin(session)
    except Exception as e:
        print(f"bootstrap_admin_on_startup failed: {e}")


@app.get("/")
async def root(request: Request):
    try:
        user = get_session_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        return RedirectResponse(url=_redirect_by_role(user.get("role")), status_code=302)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
