from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/ui/admin/managers", response_class=HTMLResponse)
async def ui_admin_managers():
    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Менеджеры и магазины</title>
  <link rel="stylesheet" href="/static/admin_managers.css">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / АДМИНИСТРИРОВАНИЕ</div>
        <h1>Менеджеры и магазины</h1>
        <div class="subline">Управление ответственными и переназначение магазинов.</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn primary" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
      </nav>
    </header>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Добавить менеджера</div>
        <div class="form-grid">
          <input id="managerName" class="input" placeholder="ФИО менеджера">
          <input id="managerEmail" class="input" placeholder="Email">
          <button id="createManagerBtn" class="action-btn primary-btn">Создать</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Справка</div>
        <div class="note">
          Здесь можно создавать менеджеров, редактировать их данные,
          удалять менеджеров и переназначать магазины на новых ответственных.
        </div>
      </div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Менеджеры</div>
        <table class="table" id="managersTable">
          <thead>
            <tr>
              <th>ФИО</th>
              <th>Email</th>
              <th>Магазинов</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-title">Магазины</div>
        <table class="table" id="storesTable">
          <thead>
            <tr>
              <th>Магазин</th>
              <th>Ответственный</th>
              <th>Назначить</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
  </div>

  <script src="/static/admin_managers.js"></script>
</body>
</html>
    """)
