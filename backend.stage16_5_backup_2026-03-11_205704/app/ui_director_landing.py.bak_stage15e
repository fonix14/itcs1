from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/ui/director", response_class=HTMLResponse)
async def ui_director_landing():
    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Операционный командный центр</title>
  <link rel="stylesheet" href="/static/director_landing.css">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / ЕДИНАЯ ТОЧКА УПРАВЛЕНИЯ</div>
        <h1 id="heroTitle">Операционный командный центр</h1>
        <div class="subline" id="heroSubtitle">Загрузка...</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn primary" href="/ui/director">Главная</a>
        <a class="btn" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
        <a class="btn" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/dashboard">Дашборд диспетчера</a>
      </nav>
    </header>

    <section class="hero-grid">
      <div class="hero-card">
        <div class="hero-title">Платформа компании</div>
        <div class="hero-text">
          Внутренний операционный портал для контроля задач, SLA, деградации данных,
          распределения ответственности и масштабирования на другие направления компании.
        </div>
      </div>

      <div class="hero-card accent-card">
        <div class="hero-title">Управленческий эффект</div>
        <div class="hero-text" id="platformValueBox">Загрузка...</div>
      </div>
    </section>

    <section class="kpi-grid">
      <div class="card kpi">
        <div class="label">Активные задачи</div>
        <div class="value" id="kpiActive">—</div>
      </div>
      <div class="card kpi">
        <div class="label">Просрочено по SLA</div>
        <div class="value" id="kpiOverdue">—</div>
      </div>
      <div class="card kpi">
        <div class="label">Открытые аномалии</div>
        <div class="value" id="kpiAnomalies">—</div>
      </div>
      <div class="card kpi">
        <div class="label">Уровень доверия</div>
        <div class="value" id="kpiTrust">—</div>
      </div>
      <div class="card kpi">
        <div class="label">Последний импорт</div>
        <div class="value value-sm" id="kpiImport">—</div>
      </div>
      <div class="card kpi">
        <div class="label">Invalid %</div>
        <div class="value" id="kpiInvalid">—</div>
      </div>
    </section>

    <section class="section">
      <div class="section-title">Модули платформы</div>
      <div id="modulesGrid" class="modules-grid"></div>
    </section>

    <section class="dual-grid">
      <div class="card">
        <div class="card-title">Roadmap развития</div>
        <div id="roadmapBox" class="roadmap-box"></div>
      </div>

      <div class="card">
        <div class="card-title">Что это даёт руководителю</div>
        <div id="valueList" class="value-list"></div>
      </div>
    </section>
  </div>

  <script src="/static/director_landing.js"></script>
</body>
</html>
    """)
