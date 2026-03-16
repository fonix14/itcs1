from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
async def admin_portal(request: Request):
    if request.session.get("role") != "admin" or not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=302)

    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ITCS Admin</title>
  <style>
    body {{
      margin:0; font-family:Inter,Arial,sans-serif;
      background:linear-gradient(180deg,#020a16 0%,#07152d 100%);
      color:#e8f0ff;
    }}
    .page {{ max-width:1500px; margin:0 auto; padding:20px; }}
    .top {{
      display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:18px;
    }}
    .nav {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .nav a, .nav button {{
      display:inline-flex; align-items:center; justify-content:center;
      text-decoration:none; color:#e8f0ff; border:1px solid rgba(120,160,255,.16);
      background:#0b1d3a; padding:10px 16px; border-radius:14px; cursor:pointer;
    }}
    .nav .primary {{ background:#5f97ff; border:none; }}
    .grid-2 {{ display:grid; grid-template-columns:1.1fr .9fr; gap:16px; margin-bottom:16px; }}
    .grid-4 {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }}
    .card {{
      background:#0b1d3a; border:1px solid rgba(120,160,255,.16); border-radius:24px; padding:18px;
      box-shadow:0 12px 32px rgba(0,0,0,.24);
    }}
    .metric-label {{ color:#9cb0d4; font-size:13px; margin-bottom:8px; }}
    .metric-value {{ font-size:24px; font-weight:700; }}
    .form-grid {{
      display:grid; grid-template-columns:1.2fr 1fr 160px 180px; gap:10px; margin-bottom:12px;
    }}
    input, select, button {{
      border-radius:14px; border:1px solid rgba(120,160,255,.16); background:#14294f;
      color:#e8f0ff; min-height:44px; padding:10px 14px; box-sizing:border-box;
    }}
    button {{ cursor:pointer; }}
    .btn-primary {{ background:#5f97ff; border:none; }}
    .btn-danger {{ background:#8d3045; border:none; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ padding:10px 8px; border-bottom:1px solid rgba(120,160,255,.08); text-align:left; vertical-align:top; }}
    th {{ color:#9cb0d4; font-weight:600; }}
    .actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .small {{ color:#9cb0d4; font-size:13px; }}
    @media (max-width:1450px) {{
      .grid-2 {{ grid-template-columns:1fr; }}
      .grid-4 {{ grid-template-columns:repeat(2,1fr); }}
      .form-grid {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="top">
      <div>
        <div style="color:#9cb0d4;font-size:12px;margin-bottom:6px;">ITCS / ADMIN</div>
        <h1 style="margin:0 0 8px;">Панель администратора</h1>
        <div class="small">Пользователи, роли, пароли и системный мониторинг.</div>
      </div>
      <div class="nav">
        <a class="primary" href="/admin">Админ</a>
        <a href="/ui/dashboard">Дашборд диспетчера</a>
        <a href="/ui/tasks">Задачи</a>
        <a href="/ui/admin/managers">Менеджеры</a>
        <form method="post" action="/logout" style="margin:0;">
          <button type="submit">Выйти</button>
        </form>
      </div>
    </div>

    <div class="grid-4">
      <div class="card"><div class="metric-label">CPU</div><div class="metric-value" id="cpuV">—</div></div>
      <div class="card"><div class="metric-label">RAM</div><div class="metric-value" id="ramV">—</div></div>
      <div class="card"><div class="metric-label">Disk free</div><div class="metric-value" id="diskV">—</div></div>
      <div class="card"><div class="metric-label">API / DB</div><div class="metric-value" id="statusV">—</div></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div style="font-weight:700;margin-bottom:12px;">Создать пользователя</div>
        <div class="form-grid">
          <input id="newFullName" placeholder="ФИО">
          <input id="newEmail" placeholder="Email">
          <select id="newRole">
            <option value="manager">manager</option>
            <option value="dispatcher">dispatcher</option>
            <option value="admin">admin</option>
          </select>
          <input id="newPassword" placeholder="Пароль">
        </div>
        <button class="btn-primary" id="createUserBtn">Создать</button>
      </div>

      <div class="card">
        <div style="font-weight:700;margin-bottom:12px;">Системная сводка</div>
        <div class="small" id="systemText">Загрузка...</div>
      </div>
    </div>

    <div class="card">
      <div style="font-weight:700;margin-bottom:12px;">Пользователи</div>
      <table id="usersTable">
        <thead>
          <tr>
            <th>ФИО</th>
            <th>Email</th>
            <th>Роль</th>
            <th>Активен</th>
            <th>Последний вход</th>
            <th>Пароль</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <script>
    function esc(v) {{
      return String(v ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function fmtDate(v) {{
      if (!v) return "—";
      try {{ return new Date(v).toLocaleString("ru-RU"); }}
      catch {{ return String(v); }}
    }}

    async function loadMetrics() {{
      const resp = await fetch("/api/admin/system/metrics", {{ cache: "no-store" }});
      const payload = await resp.json();
      if (payload.status !== "ok") return;

      document.getElementById("cpuV").innerText = payload.cpu_percent + "%";
      document.getElementById("ramV").innerText = payload.ram_percent + "%";
      document.getElementById("diskV").innerText = payload.disk_free_gb + " GB";
      document.getElementById("statusV").innerText = payload.api_status + " / " + payload.db_status;
      document.getElementById("systemText").innerText =
        `RAM: ${{payload.ram_used_gb}} / ${{payload.ram_total_gb}} GB | ` +
        `Disk: ${{payload.disk_used_gb}} / ${{payload.disk_total_gb}} GB | ` +
        `Load: ${{payload.load_1m}} / ${{payload.load_5m}} / ${{payload.load_15m}} | ` +
        `Uptime: ${{payload.uptime_seconds}} сек`;
    }}

    async function loadUsers() {{
      const resp = await fetch("/api/admin/users", {{ cache: "no-store" }});
      const payload = await resp.json();
      if (payload.status !== "ok") {{
        alert(payload.error || "Ошибка загрузки пользователей");
        return;
      }}

      const tbody = document.querySelector("#usersTable tbody");
      tbody.innerHTML = "";

      payload.data.forEach((row) => {{
        tbody.insertAdjacentHTML("beforeend", `
          <tr>
            <td><input id="full_${{row.id}}" value="${{esc(row.full_name)}}"></td>
            <td><input id="email_${{row.id}}" value="${{esc(row.email)}}"></td>
            <td>
              <select id="role_${{row.id}}">
                <option value="manager" ${{row.role === "manager" ? "selected" : ""}}>manager</option>
                <option value="dispatcher" ${{row.role === "dispatcher" ? "selected" : ""}}>dispatcher</option>
                <option value="admin" ${{row.role === "admin" ? "selected" : ""}}>admin</option>
              </select>
            </td>
            <td>
              <select id="active_${{row.id}}">
                <option value="true" ${{row.is_active ? "selected" : ""}}>true</option>
                <option value="false" ${{!row.is_active ? "selected" : ""}}>false</option>
              </select>
            </td>
            <td>${{fmtDate(row.last_login_at)}}</td>
            <td><input id="pwd_${{row.id}}" placeholder="Новый пароль"></td>
            <td>
              <div class="actions">
                <button onclick="saveUser('${{row.id}}')">Сохранить</button>
                <button onclick="setPassword('${{row.id}}')">Сменить пароль</button>
                <button class="btn-danger" onclick="deactivateUser('${{row.id}}')">Деактивировать</button>
              </div>
            </td>
          </tr>
        `);
      }});
    }}

    async function createUser() {{
      const payload = {{
        full_name: document.getElementById("newFullName").value.trim(),
        email: document.getElementById("newEmail").value.trim(),
        role: document.getElementById("newRole").value,
        password: document.getElementById("newPassword").value.trim(),
      }};

      const resp = await fetch("/api/admin/users", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      const data = await resp.json();

      if (data.status !== "ok") {{
        alert(data.error || "Ошибка создания");
        return;
      }}

      document.getElementById("newFullName").value = "";
      document.getElementById("newEmail").value = "";
      document.getElementById("newPassword").value = "";

      await loadUsers();
    }}

    async function saveUser(userId) {{
      const payload = {{
        full_name: document.getElementById(`full_${{userId}}`).value.trim(),
        email: document.getElementById(`email_${{userId}}`).value.trim(),
        role: document.getElementById(`role_${{userId}}`).value,
        is_active: document.getElementById(`active_${{userId}}`).value === "true"
      }};

      const resp = await fetch(`/api/admin/users/${{userId}}`, {{
        method: "PUT",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      const data = await resp.json();

      if (data.status !== "ok") {{
        alert(data.error || "Ошибка сохранения");
        return;
      }}

      await loadUsers();
    }}

    async function setPassword(userId) {{
      const password = document.getElementById(`pwd_${{userId}}`).value.trim();
      if (!password) {{
        alert("Введите новый пароль");
        return;
      }}

      const resp = await fetch(`/api/admin/users/${{userId}}/set-password`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ password }})
      }});
      const data = await resp.json();

      if (data.status !== "ok") {{
        alert(data.error || "Ошибка смены пароля");
        return;
      }}

      document.getElementById(`pwd_${{userId}}`).value = "";
      alert("Пароль обновлён");
    }}

    async function deactivateUser(userId) {{
      if (!confirm("Деактивировать пользователя?")) return;

      const resp = await fetch(`/api/admin/users/${{userId}}/deactivate`, {{
        method: "POST"
      }});
      const data = await resp.json();

      if (data.status !== "ok") {{
        alert(data.error || "Ошибка деактивации");
        return;
      }}

      await loadUsers();
    }}

    document.getElementById("createUserBtn").addEventListener("click", createUser);

    loadMetrics();
    loadUsers();
    setInterval(loadMetrics, 5000);
  </script>
</body>
</html>
    """
    return HTMLResponse(html)
