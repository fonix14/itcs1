from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui_command_center"])


HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>ITCS — Operations Command Center</title>
  <link rel="stylesheet" href="/static/command_center.css">
</head>
<body>
  <div class="page">
    <header class="hero">
      <div>
        <div class="eyebrow">ITCS / Stage 15A</div>
        <h1>Operations Command Center</h1>
        <p class="subtitle">
          Единый операционный портал: импорт Excel, задачи, SLA, trust level, быстрые действия и платформа для роста.
        </p>
      </div>
      <nav class="top-links">
        <a href="/ui/dashboard">Dashboard</a>
        <a href="/ui/upload">Upload</a>
        <a href="/ui/tasks">Tasks</a>
        <a href="/m/tasks">Mobile</a>
      </nav>
    </header>

    <section class="grid kpi-grid" id="kpiGrid">
      <article class="card kpi-card">
        <div class="card-title">Активные задачи</div>
        <div class="card-value" id="kpiActiveTasks">—</div>
      </article>
      <article class="card kpi-card">
        <div class="card-title">Просроченные SLA</div>
        <div class="card-value" id="kpiOverdueSla">—</div>
      </article>
      <article class="card kpi-card">
        <div class="card-title">Открытые аномалии</div>
        <div class="card-value" id="kpiAnomalies">—</div>
      </article>
      <article class="card kpi-card">
        <div class="card-title">Invalid %</div>
        <div class="card-value" id="kpiInvalidRatio">—</div>
      </article>
    </section>

    <section class="grid two-col">
      <article class="card">
        <div class="section-header">
          <h2>Trust level</h2>
          <span id="trustBadge" class="badge slate">UNKNOWN</span>
        </div>
        <div class="trust-meta" id="trustMeta">Нет данных health_state.</div>
        <div class="summary-box">
          <div class="summary-title" id="summaryTitle">Краткая управленческая сводка</div>
          <p id="summaryText">Загрузка данных…</p>
        </div>
      </article>

      <article class="card">
        <div class="section-header">
          <h2>Последний импорт</h2>
          <a class="inline-link" href="/ui/upload">Перейти к загрузке</a>
        </div>
        <dl class="meta-list">
          <div><dt>Файл</dt><dd id="lastUploadFilename">—</dd></div>
          <div><dt>Профиль</dt><dd id="lastUploadProfile">—</dd></div>
          <div><dt>Время</dt><dd id="lastUploadTime">—</dd></div>
          <div><dt>Invalid %</dt><dd id="lastUploadInvalid">—</dd></div>
        </dl>
      </article>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Быстрые действия</h2>
        <span class="helper">Один вход — все основные действия под рукой</span>
      </div>
      <div class="actions-grid" id="quickActions"></div>
    </section>

    <section class="card">
      <div class="section-header">
        <h2>Модули платформы</h2>
        <span class="helper">То, как проект можно показывать директору: не как набор URL, а как единый операционный центр</span>
      </div>
      <div class="modules-grid" id="modulesGrid"></div>
    </section>

    <section class="grid two-col" id="roadmap">
      <article class="card roadmap-card">
        <h2>Roadmap расширения</h2>
        <ul class="roadmap-list">
          <li><strong>Stage 15A:</strong> единое меню и command center.</li>
          <li><strong>Stage 15B:</strong> director dashboard и проблемные зоны.</li>
          <li><strong>Stage 15C:</strong> cleaning journal как второй модуль.</li>
          <li><strong>Stage 15D:</strong> AI summary и управленческие объяснения.</li>
        </ul>
      </article>
      <article class="card ai-card" id="ai">
        <h2>AI слой</h2>
        <p>
          На этом этапе AI можно показывать как будущую надстройку: краткие сводки после импорта,
          объяснение аномалий и ежедневный директорский обзор простым языком.
        </p>
      </article>
    </section>
  </div>

  <script src="/static/command_center.js"></script>
</body>
</html>
"""


@router.get("/ui/command-center", response_class=HTMLResponse)
async def ui_command_center():
    return HTMLResponse(HTML)
