from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/ui/tasks", response_class=HTMLResponse)
async def ui_tasks():
    html = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ITCS — Задачи</title>
  <link rel="stylesheet" href="/static/ops_unified.css?v=force20260311a">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / ЗАДАЧИ</div>
        <h1>Задачи</h1>
        <div class="subline">Единый экран контроля задач, SLA и состояния магазинов.</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn primary" href="/ui/tasks">Задачи</a>
        <a class="btn" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/dashboard">Дашборд диспетчера</a>
        <a class="btn" href="/ui/upload">Загрузка Excel</a>
      </nav>
    </header>

    <section class="card">
      <div class="toolbar-row">
        <input id="searchInput" class="input" placeholder="Поиск по Portal ID / магазину / статусу">
        <button id="refreshBtn" class="action-btn">Обновить</button>
      </div>
      <div class="toolbar-meta">
        <span id="tasksCount">Найдено задач: —</span>
        <span>Автообновление: 15 сек</span>
      </div>
    </section>

    <section class="card">
      <table class="table" id="tasksTable">
        <thead>
          <tr>
            <th>ID</th>
            <th>Portal ID</th>
            <th>Магазин</th>
            <th>Статус</th>
            <th>SLA</th>
            <th>Последнее обновление</th>
            <th>Открыть</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </section>
  </div>

  <script src="/static/ui_tasks_fixed.js?v=force20260311a"></script>
</body>
</html>
    """
    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
