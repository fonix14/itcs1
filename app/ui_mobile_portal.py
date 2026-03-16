from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse

from app.auth import require_manager_or_dispatcher

BASE_DIR = Path(__file__).resolve().parent
router = APIRouter(tags=["ui-mobile-portal"])


@router.get("/m/tasks", response_class=HTMLResponse, dependencies=[Depends(require_manager_or_dispatcher)])
async def mobile_tasks(request: Request):
    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Мои заявки</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp4">
  <style>
    body{margin:0;background:radial-gradient(circle at top,#0a1930,#040b16);font-family:Arial,sans-serif;color:#fff}
    .page{max-width:980px;margin:0 auto;padding:24px}
    .title{font-size:28px;font-weight:800;margin:0 0 6px}
    .sub{color:#9db2d1;margin:0 0 18px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
    .input,.select,.btn{width:100%;box-sizing:border-box;padding:12px;border-radius:12px;border:1px solid #223252;background:#0f1b31;color:#fff}
    .chips{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
    .chip{padding:10px 14px;border-radius:999px;border:1px solid #223252;background:#0f1b31;color:#fff;cursor:pointer}
    .chip.active{background:#4f8cff;border-color:#4f8cff}
    .meta{color:#9db2d1;margin-bottom:14px}
    .task-list{display:grid;gap:12px}
    .task{display:block;text-decoration:none;color:#fff;background:#0f1b31;border:1px solid #223252;border-radius:18px;padding:16px}
    .task-top{display:flex;justify-content:space-between;gap:12px;margin-bottom:10px}
    .task-title{font-size:18px;font-weight:700}
    .task-store{color:#9db2d1;font-size:14px}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .label{color:#9db2d1;font-size:12px;margin-bottom:4px}
    .value{font-size:15px}
    .status{padding:6px 10px;border-radius:999px;background:rgba(79,140,255,.14);border:1px solid rgba(79,140,255,.28)}
    .sla-red{color:#fecaca}
    .sla-yellow{color:#fde68a}
    .sla-green{color:#86efac}
    .empty,.error{background:#0f1b31;border:1px solid #223252;border-radius:18px;padding:16px}
    @media (max-width:700px){.grid,.grid2,.task-top{grid-template-columns:1fr;display:grid}}
  </style>
</head>
<body>
  <div class="page">
    <h1 class="title">Мои заявки</h1>
    <div class="sub">Личный кабинет менеджера. Только ваши задачи и переход в полную карточку заявки.</div>

    <div class="grid">
      <input id="q" class="input" placeholder="Поиск по Portal ID / Магазину">
      <select id="sort" class="select">
        <option value="sla">Сортировка: по SLA</option>
        <option value="new">Сортировка: по последним</option>
      </select>
    </div>

    <div class="grid">
      <button class="btn" onclick="loadTasks()">Обновить</button>
      <button class="btn" onclick="installPwa()">Установить на экран</button>
    </div>

    <div class="chips">
      <button class="chip active" onclick="setFilter('all', this)">Все</button>
      <button class="chip" onclick="setFilter('accepted', this)">Принятые</button>
      <button class="chip" onclick="setFilter('open', this)">Открытые</button>
      <button class="chip" onclick="setFilter('overdue', this)">Просроченные</button>
    </div>

    <div id="meta" class="meta">Загрузка...</div>
    <div id="tasks_container" class="task-list">Загрузка...</div>
  </div>

  <script src="/static/mobile_tasks_portal.js?v=lkfix4"></script>
</body>
</html>
    """)


@router.get("/manifest.webmanifest")
async def manifest():
    return FileResponse(
        str(BASE_DIR / "static" / "manifest.webmanifest"),
        media_type="application/manifest+json",
    )


@router.get("/sw.js")
async def service_worker():
    return FileResponse(
        str(BASE_DIR / "static" / "sw.js"),
        media_type="application/javascript",
    )
