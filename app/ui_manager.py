from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


@router.get("/manager/tasks", response_class=HTMLResponse)
async def manager_tasks_page(request: Request):
    if request.session.get("role") != "manager" or not request.session.get("user_id"):
        return RedirectResponse("/manager/login", status_code=302)

    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Мои заявки</title>
  <style>
    body {{
      margin:0; font-family:Inter,Arial,sans-serif;
      background:linear-gradient(180deg,#020a16 0%,#07152d 100%);
      color:#e8f0ff;
    }}
    .page {{ max-width:1200px; margin:0 auto; padding:20px; }}
    .top {{
      display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:18px;
    }}
    .card {{
      background:#0b1d3a; border:1px solid rgba(120,160,255,.16); border-radius:24px; padding:18px;
      box-shadow:0 12px 32px rgba(0,0,0,.24); margin-bottom:16px;
    }}
    .controls {{
      display:grid; grid-template-columns:1fr 220px auto; gap:12px; margin-bottom:12px;
    }}
    input, select, button {{
      border-radius:14px; border:1px solid rgba(120,160,255,.16); background:#14294f;
      color:#e8f0ff; min-height:44px; padding:10px 14px; box-sizing:border-box;
    }}
    button {{ cursor:pointer; }}
    .btn-primary {{ background:#5f97ff; border:none; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }}
    .metric {{ background:#0b1d3a; border:1px solid rgba(120,160,255,.16); border-radius:18px; padding:14px; }}
    .metric-label {{ color:#9cb0d4; font-size:13px; margin-bottom:8px; }}
    .metric-value {{ font-size:24px; font-weight:700; }}
    .task {{
      background:#0b1d3a; border:1px solid rgba(120,160,255,.16); border-radius:20px; padding:16px; margin-bottom:12px;
    }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:10px; }}
    .pill {{
      display:inline-flex; padding:6px 10px; border-radius:999px; font-size:12px;
      border:1px solid rgba(120,160,255,.16);
    }}
    .risk-overdue {{ background:rgba(220,53,69,.14); color:#ff9aa6; }}
    .risk-warning {{ background:rgba(255,193,7,.14); color:#ffd666; }}
    .risk-normal {{ background:rgba(57,185,122,.14); color:#8ff0bc; }}
    .risk-none {{ background:rgba(148,163,184,.12); color:#c8d1e2; }}
    .status {{ color:#cfe0ff; font-weight:600; }}
    .actions {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }}
    .small {{ color:#9cb0d4; font-size:13px; }}
    .logout-form {{ margin:0; }}
    @media (max-width:1100px) {{
      .controls {{ grid-template-columns:1fr; }}
      .grid {{ grid-template-columns:repeat(2,1fr); }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="top">
      <div>
        <div style="color:#9cb0d4;font-size:12px;margin-bottom:6px;">ITCS / МЕНЕДЖЕР</div>
        <h1 style="margin:0 0 8px;">Мои заявки</h1>
        <div class="small">Менеджер: {request.session.get("display_name","Менеджер")}</div>
      </div>
      <form class="logout-form" method="post" action="/manager/logout">
        <button type="submit">Выйти</button>
      </form>
    </div>

    <div class="grid">
      <div class="metric"><div class="metric-label">Всего</div><div class="metric-value" id="m_total">—</div></div>
      <div class="metric"><div class="metric-label">В работе</div><div class="metric-value" id="m_progress">—</div></div>
      <div class="metric"><div class="metric-label">Ожидают</div><div class="metric-value" id="m_waiting">—</div></div>
      <div class="metric"><div class="metric-label">Просрочено</div><div class="metric-value" id="m_overdue">—</div></div>
    </div>

    <div class="card">
      <div class="controls">
        <input id="searchInput" placeholder="Поиск по Portal ID / магазину">
        <select id="riskFilter">
          <option value="">Все риски</option>
          <option value="warning">warning</option>
          <option value="overdue">overdue</option>
          <option value="normal">normal</option>
          <option value="none">none</option>
        </select>
        <button class="btn-primary" id="refreshBtn">Обновить</button>
      </div>
      <div id="tasksBox"></div>
    </div>
  </div>

  <script>
    let allTasks = [];

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

    function riskClass(v) {{
      return "risk-" + String(v || "none");
    }}

    function renderSummary(items) {{
      document.getElementById("m_total").innerText = items.length;
      document.getElementById("m_progress").innerText = items.filter(x => x.internal_status === "in_progress").length;
      document.getElementById("m_waiting").innerText = items.filter(x => x.internal_status === "waiting").length;
      document.getElementById("m_overdue").innerText = items.filter(x => x.risk_state === "overdue").length;
    }}

    function renderTasks(items) {{
      const box = document.getElementById("tasksBox");
      box.innerHTML = "";

      if (!items.length) {{
        box.innerHTML = '<div class="small">Нет задач.</div>';
        return;
      }}

      items.forEach((row) => {{
        const actions = row.internal_status === "done"
          ? ''
          : `
            <div class="actions">
              <button onclick="claimTask('${{row.id}}')">В работу</button>
              <button onclick="setStatus('${{row.id}}','waiting')">Пауза</button>
              <button onclick="setStatus('${{row.id}}','done')">Готово</button>
            </div>
          `;

        box.insertAdjacentHTML("beforeend", `
          <div class="task">
            <div class="row">
              <div><strong>Магазин:</strong> ${{esc(row.store_no || "—")}}</div>
              <div><strong>Portal ID:</strong> ${{esc(row.portal_task_id || "—")}}</div>
            </div>
            <div class="row">
              <div><span class="pill ${{riskClass(row.risk_state)}}">${{esc(row.risk_state || "none")}}</span></div>
              <div class="status">Work: ${{esc(row.internal_status || "new")}}</div>
              <div class="small">SLA: ${{fmtDate(row.sla_at)}}</div>
            </div>
            <div class="small">Последнее обновление: ${{fmtDate(row.last_seen_at)}}</div>
            ${{actions}}
          </div>
        `);
      }});
    }}

    function applyFilter() {{
      const q = document.getElementById("searchInput").value.trim().toLowerCase();
      const risk = document.getElementById("riskFilter").value.trim().toLowerCase();

      const filtered = allTasks.filter((row) => {{
        const hay = [row.portal_task_id, row.store_no].map(x => String(x ?? "").toLowerCase()).join(" | ");
        return (!q || hay.includes(q)) && (!risk || String(row.risk_state ?? "").toLowerCase() === risk);
      }});

      renderSummary(filtered);
      renderTasks(filtered);
    }}

    async function loadTasks() {{
      const resp = await fetch("/api/manager/tasks", {{ cache: "no-store" }});
      const payload = await resp.json();

      if (payload.status !== "ok") {{
        document.getElementById("tasksBox").innerHTML = '<div class="small">Ошибка загрузки.</div>';
        return;
      }}

      allTasks = Array.isArray(payload.data) ? payload.data : [];
      applyFilter();
    }}

    async function claimTask(taskId) {{
      const resp = await fetch(`/api/manager/tasks/${{taskId}}/claim`, {{ method: "POST" }});
      const payload = await resp.json();
      if (payload.status !== "ok") {{
        alert(payload.error || "Ошибка");
        return;
      }}
      await loadTasks();
    }}

    async function setStatus(taskId, internalStatus) {{
      const resp = await fetch(`/api/manager/tasks/${{taskId}}/status`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ internal_status: internalStatus }})
      }});
      const payload = await resp.json();
      if (payload.status !== "ok") {{
        alert(payload.error || "Ошибка");
        return;
      }}
      await loadTasks();
    }}

    document.getElementById("refreshBtn").addEventListener("click", loadTasks);
    document.getElementById("searchInput").addEventListener("input", applyFilter);
    document.getElementById("riskFilter").addEventListener("change", applyFilter);

    loadTasks();
    setInterval(loadTasks, 15000);
  </script>
</body>
</html>
    """
    return HTMLResponse(html)


@router.get("/m/tasks")
async def legacy_mobile_redirect():
    return RedirectResponse("/manager/tasks", status_code=302)
