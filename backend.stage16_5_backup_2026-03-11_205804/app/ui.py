from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

API_BASE = os.getenv("UI_API_BASE", "http://api:8080")
UPLOAD_ENDPOINT = "/api/portal_l4_uploads"

HTML_HEAD = """<!doctype html>
<html lang=\"ru\">
<head>
<meta charset=\"utf-8\"/>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
<title>Загрузка Excel</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial; margin:20px; max-width:960px}
.card{border:1px solid #ddd; border-radius:12px; padding:16px; margin:16px 0}
.btn{padding:10px 14px; border-radius:8px; border:1px solid #333; background:#111; color:#fff; cursor:pointer; text-decoration:none}
.btn2{padding:10px 14px; border-radius:8px; border:1px solid #333; background:#fff; color:#111; cursor:pointer; text-decoration:none}
pre{background:#f6f6f6; padding:12px; border-radius:8px; overflow:auto}
.err{color:#b00020}
.ok{color:#0b6}
</style>
</head>
<body>
"""

HTML_FOOT = """
</body>
</html>
"""


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


@router.get("/ui")
async def ui_home():
    return RedirectResponse(url="/ui/director", status_code=302)


@router.get("/ui/upload", response_class=HTMLResponse)
async def upload_form():
    return HTML_HEAD + """
    <h1>Загрузка Excel</h1>
    <div class="card">
        <form action="/ui/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".xlsx" required />
            <br/><br/>
            <button class="btn" type="submit">Загрузить</button>
            <a class="btn2" href="/ui/director">Назад в центр</a>
        </form>
    </div>
    """ + HTML_FOOT


@router.post("/ui/upload", response_class=HTMLResponse)
async def upload_submit(file: UploadFile = File(...)):
    filename = file.filename or "upload.xlsx"

    if not filename.lower().endswith(".xlsx"):
        return HTML_HEAD + """
        <div class="card err">Файл должен быть в формате .xlsx</div>
        <a class="btn2" href="/ui/upload">Назад</a>
        """ + HTML_FOOT

    try:
        content = await file.read()
    except Exception as e:
        return HTML_HEAD + f"""
        <div class="card err">Ошибка чтения файла: {esc(str(e))}</div>
        <a class="btn2" href="/ui/upload">Назад</a>
        """ + HTML_FOOT

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{API_BASE}{UPLOAD_ENDPOINT}",
                files={
                    "file": (
                        filename,
                        content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
    except Exception as e:
        return HTML_HEAD + f"""
        <div class="card err">Ошибка обращения к API: {esc(str(e))}</div>
        <a class="btn2" href="/ui/upload">Назад</a>
        """ + HTML_FOOT

    if resp.status_code >= 400:
        return HTML_HEAD + f"""
        <div class="card err">API вернул {resp.status_code}</div>
        <pre>{esc(resp.text)}</pre>
        <a class="btn2" href="/ui/upload">Назад</a>
        """ + HTML_FOOT

    try:
        data = resp.json()
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        pretty = resp.text

    return HTML_HEAD + f"""
    <div class="card ok">Файл успешно загружен</div>
    <pre>{esc(pretty)}</pre>
    <a class="btn2" href="/ui/upload">Загрузить ещё</a>
    <a class="btn" href="/ui/director">Вернуться в центр</a>
    """ + HTML_FOOT
