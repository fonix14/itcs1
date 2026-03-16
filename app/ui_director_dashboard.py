from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth_ui import require_ui_dispatcher

router = APIRouter()


@router.get("/ui/director/dashboard", response_class=HTMLResponse)
async def ui_director_dashboard(request: Request):
    guard = require_ui_dispatcher(request)
    if not isinstance(guard, dict):
        return guard

    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Операционный обзор</title>
  <link rel="stylesheet" href="/static/director_dashboard.css">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp1">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp-final">
  <link rel="stylesheet" href="/static/director_dashboard.css?v=dir-final">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / ОПЕРАЦИОННЫЙ ОБЗОР</div>
        <h1 style="font-size:26px;line-height:1.08;margin:0;">Операционный обзор</h1>
        <div class="subline"><span style="font-size:13px;line-height:1.4;">Сводка по задачам, SLA, импорту и системным рискам.</span></div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn primary" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
        <a class="btn" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/dashboard">Дашборд диспетчера</a>
        <a class="btn" href="/ui/admin/profile">Админ</a>
        <a class="btn" href="/logout">Выход</a>
      </nav>
    </header>

    <div id="directorDashboardApp">Загрузка...</div>

    <script src="/static/director_dashboard.js"></script>
  </div>
</body>
</html>
    """)
