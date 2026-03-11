from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/ui/director/dashboard", response_class=HTMLResponse)
async def ui_director_dashboard():
    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Операционный обзор</title>
  <link rel="stylesheet" href="/static/director_dashboard.css">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / ОПЕРАЦИОННЫЙ ОБЗОР</div>
        <h1>Операционный обзор</h1>
        <div class="subline" id="generatedAtLine">Обновление данных...</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn primary" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
        <a class="btn" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/dashboard">Дашборд диспетчера</a>
      </nav>
    </header>

    <section id="riskBanner" class="risk-banner hidden"></section>

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
        <div class="label">Невалидные строки</div>
        <div class="value" id="kpiInvalid">—</div>
      </div>

      <div class="card kpi">
        <div class="label">Ожидают аномалии</div>
        <div class="value" id="kpiAnomalies">—</div>
      </div>

      <div class="card kpi">
        <div class="label">Уровень доверия</div>
        <div class="value trust-value" id="kpiTrust">—</div>
        <div class="trust-badge trust-unknown" id="trustBadge">UNKNOWN</div>
      </div>

      <div class="card kpi">
        <div class="label">Последний импорт</div>
        <div class="value value-sm" id="kpiImport">—</div>
      </div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Управленческая сводка</div>
        <div id="summaryBox" class="summary-box">Загрузка...</div>
      </div>

      <div class="card">
        <div class="card-title">Быстрые действия</div>
        <div class="actions">
          <a class="action-btn" href="/ui/tasks">Открыть задачи</a>
          <a class="action-btn" href="/ui/admin/managers">Открыть менеджеров</a>
          <a class="action-btn" href="/ui/dashboard">Дашборд диспетчера</a>
          <a class="action-btn" href="/m/tasks">Мобильный вид</a>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="card-title">Требует внимания сейчас</div>
      <div id="attentionGrid" class="attention-grid">
        <div class="attention-empty">Нет данных.</div>
      </div>
    </section>

    <section class="analytics-grid">
      <div class="card">
        <div class="card-title">Сегодня под риском</div>
        <div class="risk-metrics">
          <div class="risk-metric">
            <div class="risk-metric-label">SLA просрочено</div>
            <div class="risk-metric-value" id="todayOverdue">—</div>
          </div>
          <div class="risk-metric">
            <div class="risk-metric-label">Открытые аномалии</div>
            <div class="risk-metric-value" id="todayAnomalies">—</div>
          </div>
          <div class="risk-metric">
            <div class="risk-metric-label">Активные задачи</div>
            <div class="risk-metric-value" id="todayActive">—</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Последние 7 дней</div>
        <div class="week-grid">
          <div class="week-item">
            <div class="week-label">Загрузок</div>
            <div class="week-value" id="weekUploads">—</div>
          </div>
          <div class="week-item">
            <div class="week-label">Всего строк</div>
            <div class="week-value" id="weekRows">—</div>
          </div>
          <div class="week-item">
            <div class="week-label">Невалидных строк</div>
            <div class="week-value" id="weekInvalidRows">—</div>
          </div>
          <div class="week-item">
            <div class="week-label">Средний invalid %</div>
            <div class="week-value" id="weekInvalidAvg">—</div>
          </div>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="card-title">Динамика последних загрузок</div>
      <div id="uploadsMiniChart" class="mini-chart"></div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Проблемные магазины</div>
        <table class="table" id="storesTable">
          <thead>
            <tr>
              <th>Магазин</th>
              <th>Открытых задач</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-title">Нагрузка по менеджерам</div>
        <table class="table" id="managersTable">
          <thead>
            <tr>
              <th>Менеджер</th>
              <th>Открытых задач</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <div class="card-title">Последние загрузки</div>
      <table class="table" id="uploadsTable">
        <thead>
          <tr>
            <th>Файл</th>
            <th>Профиль</th>
            <th>Загружено</th>
            <th>Невалидные строки</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </section>
  </div>

  <script src="/static/director_dashboard.js"></script>
</body>
</html>
    """)
