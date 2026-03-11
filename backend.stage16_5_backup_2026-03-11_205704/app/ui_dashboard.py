from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/ui/dashboard", response_class=HTMLResponse)
async def ui_dashboard():
    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ITCS Ops Dashboard</title>
  <link rel="stylesheet" href="/static/ops_unified.css">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / ПАНЕЛЬ ДИСПЕТЧЕРА</div>
        <h1>ITCS Ops Dashboard</h1>
        <div class="subline">Панель диспетчера: импорт, аномалии, trust level, SLA контроль.</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
        <a class="btn" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn primary" href="/ui/dashboard">Дашборд диспетчера</a>
      </nav>
    </header>

    <section class="card">
      <div class="actions">
        <a class="action-btn" href="/ui/upload">Загрузить Excel</a>
        <a class="action-btn" href="/ui/tasks">Открыть задачи</a>
        <a class="action-btn" href="/ui/director/dashboard">Операционный обзор</a>
      </div>
    </section>

    <section class="kpi-grid" id="kpiGrid">
      <div class="card kpi"><div class="label">Всего задач</div><div class="value" id="kpiTasks">—</div></div>
      <div class="card kpi"><div class="label">Всего импортов</div><div class="value" id="kpiUploads">—</div></div>
      <div class="card kpi"><div class="label">Открытые аномалии</div><div class="value" id="kpiAnomalies">—</div></div>
      <div class="card kpi"><div class="label">Invalid % последнего импорта</div><div class="value" id="kpiInvalid">—</div></div>
      <div class="card kpi"><div class="label">SLA overdue</div><div class="value" id="kpiOverdue">—</div></div>
      <div class="card kpi"><div class="label">SLA &lt; 24ч</div><div class="value" id="kpiRisk24">—</div></div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Health summary</div>
        <div id="healthSummary" class="summary-box">Загрузка...</div>
      </div>
      <div class="card">
        <div class="card-title">Warnings</div>
        <div id="warningsBox" class="summary-box">Загрузка...</div>
      </div>
    </section>

    <section class="card">
      <div class="card-title">Нагрузка по менеджерам</div>
      <table class="table" id="managerLoadTable">
        <thead>
          <tr>
            <th>Менеджер</th>
            <th>Активные</th>
            <th>Просрочено</th>
            <th>Риск &lt; 24ч</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </section>
  </div>

  <script src="/static/ui_dashboard_fixed.js"></script>
</body>
</html>
    """)
