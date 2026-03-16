from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth_ui import require_ui_dispatcher

router = APIRouter()


@router.get("/ui/admin/managers", response_class=HTMLResponse)
async def ui_admin_managers(request: Request):
    guard = require_ui_dispatcher(request)
    if not isinstance(guard, dict):
        return guard

    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Менеджеры и магазины</title>
  <link rel="stylesheet" href="/static/admin_managers_cards.css?v=cards1">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp2">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp-final">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / АДМИНИСТРИРОВАНИЕ</div>
        <h1 style="font-size:32px;line-height:1.08;margin:0;">Менеджеры и магазины</h1>
        <div class="subline">Управление менеджерами, паролями и распределением магазинов.</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
        <a class="btn primary" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/dashboard">Дашборд диспетчера</a>
        <a class="btn" href="/ui/admin/profile">Админ</a>
        <a class="btn" href="/logout">Выход</a>
      </nav>
    </header>

    <section class="grid-top">
      <div class="card">
        <div class="card-title">Добавить менеджера</div>
        <div class="form-grid">
          <input id="managerName" class="input" placeholder="ФИО менеджера">
          <input id="managerEmail" class="input" placeholder="Email">
          <button id="createManagerBtn" class="action-btn primary-btn">Создать</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Поиск</div>
        <div class="form-grid form-grid-2">
          <input id="managerSearch" class="input" placeholder="Поиск по менеджеру">
          <input id="storeSearch" class="input" placeholder="Поиск по магазину">
        </div>
      </div>
    </section>

    <section class="main-grid">
      <div class="card">
        <div class="card-head">
          <div class="card-title">Менеджеры</div>
          <div id="managersCount" class="muted">—</div>
        </div>
        <div id="managersCards" class="manager-cards">Загрузка...</div>
      </div>

      <div class="card">
        <div class="card-head">
          <div class="card-title">Магазины</div>
          <div id="storesCount" class="muted">—</div>
        </div>
        <div id="storesList" class="stores-list">Загрузка...</div>
      </div>
    </section>
  </div>

  <div id="passwordModal" class="modal hidden">
    <div class="modal-backdrop" onclick="closePasswordModal()"></div>
    <div class="modal-dialog">
      <div class="modal-header">
        <div>
          <div class="modal-title">Управление паролем</div>
          <div id="passwordModalSub" class="modal-sub">Менеджер</div>
        </div>
        <button class="icon-btn" onclick="closePasswordModal()">✕</button>
      </div>

      <div class="modal-body">
        <input id="modalPasswordInput" class="input" type="password" placeholder="Новый пароль">

        <div class="modal-actions-grid">
          <button class="mini-btn" onclick="modalGeneratePassword()">Сгенерировать</button>
          <button class="mini-btn" id="modalToggleBtn" onclick="modalTogglePassword()">Показать</button>
          <button class="mini-btn" onclick="modalCopyPassword()">Копировать</button>
        </div>

        <div class="modal-actions-grid">
          <button class="mini-btn primary-btn" onclick="modalSavePassword()">Сохранить пароль</button>
          <button class="mini-btn" onclick="closePasswordModal()">Отмена</button>
        </div>
      </div>
    </div>
  </div>

  <script src="/static/admin_managers_cards.js?v=cards1"></script>
</body>
</html>
    """)
