from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_manager import verify_password
from app.authz import get_current_session_user
from app.db import get_db

router = APIRouter(tags=["unified_auth"])


def login_html(error: str = "") -> str:
    err = f'<div style="color:#ff9aa6;margin-bottom:12px;">{error}</div>' if error else ""
    return f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ITCS — Вход</title>
  <style>
    body {{
      margin:0; font-family:Inter,Arial,sans-serif;
      background:linear-gradient(180deg,#020a16 0%,#07152d 100%);
      color:#e8f0ff; display:flex; align-items:center; justify-content:center; min-height:100vh;
    }}
    .card {{
      width:100%; max-width:430px; background:#0b1d3a;
      border:1px solid rgba(120,160,255,.16);
      border-radius:24px; padding:24px; box-shadow:0 12px 32px rgba(0,0,0,.24);
    }}
    h1 {{ margin:0 0 8px; }}
    .sub {{ color:#9cb0d4; margin-bottom:16px; }}
    input {{
      width:100%; box-sizing:border-box; margin-bottom:12px; border-radius:14px;
      border:1px solid rgba(120,160,255,.16); background:#14294f; color:#e8f0ff;
      padding:12px 14px; min-height:46px;
    }}
    button {{
      width:100%; min-height:46px; border:none; border-radius:14px;
      background:#5f97ff; color:white; cursor:pointer; font-weight:600;
    }}
  </style>
</head>
<body>
  <form class="card" method="post" action="/login">
    <div style="color:#9cb0d4;font-size:12px;margin-bottom:6px;">ITCS / ЕДИНЫЙ ВХОД</div>
    <h1>Вход в портал</h1>
    <div class="sub">Авторизация для администратора, диспетчера и менеджера.</div>
    {err}
    <input type="email" name="email" placeholder="Email" autocomplete="username" required>
    <input type="password" name="password" placeholder="Пароль" autocomplete="current-password" required>
    <button type="submit">Войти</button>
  </form>
</body>
</html>
    """


def redirect_by_role(role: str) -> str:
    if role == "admin":
        return "/admin"
    if role == "dispatcher":
        return "/ui/dashboard"
    if role == "manager":
        return "/manager/tasks"
    return "/login"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    role = request.session.get("role")
    if role:
        return RedirectResponse(redirect_by_role(role), status_code=302)
    return HTMLResponse(login_html())


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            text("""
                select
                    id::text as id,
                    email,
                    role::text as role,
                    coalesce(display_name, full_name, email) as display_name,
                    password_hash,
                    is_active
                from users
                where lower(email) = lower(:email)
                limit 1
            """),
            {"email": email.strip()},
        )
    ).mappings().first()

    if not row:
        return HTMLResponse(login_html("Неверный логин или пароль"), status_code=401)

    if not row["is_active"]:
        return HTMLResponse(login_html("Пользователь деактивирован"), status_code=403)

    if not verify_password(password, row["password_hash"]):
        return HTMLResponse(login_html("Неверный логин или пароль"), status_code=401)

    request.session.clear()
    request.session["user_id"] = row["id"]
    request.session["role"] = row["role"]
    request.session["display_name"] = row["display_name"]
    request.session["email"] = row["email"]

    await db.execute(
        text("""
            update users
            set last_login_at = now()
            where id = :id
        """),
        {"id": row["id"]},
    )
    await db.commit()

    return RedirectResponse(redirect_by_role(row["role"]), status_code=302)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@router.get("/api/auth/me")
async def auth_me(request: Request):
    try:
        user = get_current_session_user(request)
        return {"status": "ok", **user}
    except Exception:
        return {"status": "anonymous"}
