function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("ru-RU");
  } catch {
    return String(value);
  }
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadTasks(overdueOnly = false) {
  const app = document.getElementById("tasksApp");
  if (!app) return;

  app.innerHTML = "Загрузка...";

  try {
    const resp = await fetch(`/api/tasks?overdue_only=${overdueOnly ? "true" : "false"}`, {
      credentials: "same-origin"
    });
    const payload = await resp.json();

    if (payload.status !== "ok") {
      app.innerHTML = `<div class="card">Ошибка загрузки: ${esc(payload.error || "unknown error")}</div>`;
      return;
    }

    const rows = payload.data || [];

    app.innerHTML = `
      <style>
        .tasks-toolbar{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px;margin-bottom:16px}
        .tasks-btn{
          text-decoration:none;color:#e8eef8;border:1px solid #223252;background:rgba(17,26,43,.9);
          padding:10px 14px;border-radius:14px;cursor:pointer
        }
        .tasks-btn.active{background:#4f8cff;border-color:#4f8cff}
        .tasks-card{
          background:rgba(15,27,49,.94);
          border:1px solid #223252;
          border-radius:20px;
          padding:18px;
          box-shadow:0 14px 40px rgba(0,0,0,.22);
        }
        .tasks-table{width:100%;border-collapse:collapse}
        .tasks-table th,.tasks-table td{
          text-align:left;padding:10px 8px;border-bottom:1px solid rgba(34,50,82,.75);font-size:14px;vertical-align:top
        }
        .tasks-table th{color:#93a4bf}
        .task-link{
          display:inline-block;text-decoration:none;color:#fff;background:#4f8cff;
          padding:8px 12px;border-radius:10px
        }
      </style>

      <div class="tasks-toolbar">
        <button class="tasks-btn ${overdueOnly ? "" : "active"}" onclick="loadTasks(false)">Все задачи</button>
        <button class="tasks-btn ${overdueOnly ? "active" : ""}" onclick="loadTasks(true)">Только просроченные</button>
      </div>

      <div class="tasks-card">
        <table class="tasks-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Portal task</th>
              <th>Магазин</th>
              <th>Менеджер</th>
              <th>Статус</th>
              <th>SLA</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map(item => `
              <tr>
                <td>${esc(item.id ?? "—")}</td>
                <td>${esc(item.portal_task_id ?? "—")}</td>
                <td>${esc(item.store_no ?? "—")}</td>
                <td>${esc(item.manager_name ?? "—")}</td>
                <td>${esc(item.status ?? "—")}</td>
                <td>${esc(formatDate(item.sla))}</td>
                <td><a href="/ui/task/${encodeURIComponent(item.id)}" class="task-link">Открыть</a></td>
              </tr>
            `).join("") : `
              <tr><td colspan="7">Нет данных</td></tr>
            `}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    app.innerHTML = `<div class="card">Непредвиденная ошибка: ${esc(e.message || String(e))}</div>`;
    console.error(e);
  }
}

window.addEventListener("load", () => loadTasks(false));
