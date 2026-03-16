from __future__ import annotations

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.db import SessionLocal
from app.auth import verify_password
from app.auth_ui import get_session_user

router = APIRouter()

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ITCS Login</title>
  <style>
    body{
      margin:0;
      background: radial-gradient(circle at top,#0a1930,#040b16);
      font-family: Arial, sans-serif;
      height:100vh;
      display:flex;
      align-items:center;
      justify-content:center;
      color:white;
    }
    .card{
      background:#0f1b31;
      padding:40px;
      border-radius:16px;
      width:360px;
      box-shadow:0 0 40px rgba(0,0,0,.6);
      border:1px solid #23385e;
    }
    h2{
      margin:0 0 20px 0;
      font-size:28px;
    }
    .sub{
      color:#9db2d1;
      margin:0 0 20px 0;
      font-size:14px;
    }
    input{
      width:100%;
      padding:12px;
      margin-bottom:15px;
      border-radius:10px;
      border:1px solid #23385e;
      background:#081224;
      color:white;
      box-sizing:border-box;
    }
    button{
      width:100%;
      padding:12px;
      border:none;
      border-radius:10px;
      background:#4f8cff;
      color:white;
      font-weight:bold;
      cursor:pointer;
    }
    button:hover{
      background:#3a73db;
    }
    .error{
      background:#4a1620;
      color:#ffd7de;
      border:1px solid #6b2432;
      padding:10px 12px;
      border-radius:10px;
      margin-bottom:14px;
      font-size:14px;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>ITCS Login</h2>
    <div class="sub">Вход в систему контроля заявок</div>
    __ERROR_BLOCK__
    <form method="post">
      <input name="email" type="text" placeholder="Email" required>
      <input name="password" type="password" placeholder="Password" required>
      <button type="submit">Login</button>
    </form>
  </div>
</body>
</html>
"""


def render_login(error: str | None = None) -> HTMLResponse:
    error_block = f'<div class="error">{error}</div>' if error else ""
    html = LOGIN_HTML.replace("__ERROR_BLOCK__", error_block)
    return HTMLResponse(html)


def redirect_by_role(role: str | None) -> str:
    role = (role or "").strip().lower()
    if role in {"admin", "dispatcher"}:
        return "/ui/dashboard"
    if role == "manager":
        return "/m/tasks"
    return "/login"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url=redirect_by_role(user["role"]), status_code=303)
    return render_login()


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    async with SessionLocal() as session:
        result = await session.execute(
            text(
                """
                select
                    id::text as id,
                    email,
                    full_name,
                    role,
                    password_salt,
                    password_hash,
                    is_active
                from users
                where lower(email) = lower(:email)
                limit 1
                """
            ),
            {"email": email.strip()},
        )
        user = result.mappings().first()

        if not user:
            return render_login("Неверный логин или пароль")

        if not user["is_active"]:
            return render_login("Учетная запись отключена")

        ok = verify_password(
            password=password,
            salt=user["password_salt"],
            password_hash=user["password_hash"],
        )
        if not ok:
            return render_login("Неверный логин или пароль")

        request.session.clear()
        request.session["user_id"] = str(user["id"])
        request.session["role"] = str(user["role"]).strip().lower()
        request.session["email"] = user["email"]
        request.session["full_name"] = user["full_name"]

        response = RedirectResponse(
            url=redirect_by_role(str(user["role"]).strip().lower()),
            status_code=303,
        )
        return response


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
