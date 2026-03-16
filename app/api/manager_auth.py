from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["manager_auth_legacy"])


@router.get("/manager/login")
async def manager_login_page_redirect():
    return RedirectResponse("/login", status_code=302)


@router.post("/manager/login")
async def manager_login_submit_redirect():
    return RedirectResponse("/login", status_code=302)


@router.post("/manager/logout")
async def manager_logout_redirect():
    return RedirectResponse("/logout", status_code=302)
