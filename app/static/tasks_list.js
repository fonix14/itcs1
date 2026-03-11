function formatDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString(); } catch (e) { return String(value); }
}

async function loadTasks(overdueOnly = false) {
  const body = document.getElementById("tasks_body");
  body.innerHTML = '<tr><td colspan="7" class="muted">Загрузка...</td></tr>';
  try {
    const resp = await fetch(`/api/tasks?overdue_only=${overdueOnly ? "true" : "false"}`);
    const payload = await resp.json();
    if (payload.status !== "ok") throw new Error(payload.error || "Load failed");

    const rows = payload.data || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="7" class="muted">Нет данных</td></tr>';
      return;
    }

    body.innerHTML = "";
    for (const item of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${item.id ?? "—"}</td>
        <td>${item.portal_task_id ?? "—"}</td>
        <td>${item.store_no ?? "—"}</td>
        <td>${item.manager_name ?? "—"}</td>
        <td>${item.status ?? "—"}</td>
        <td>${formatDate(item.sla)}</td>
        <td><a href="/ui/task/${item.id}" class="btn">Открыть</a></td>
      `;
      body.appendChild(tr);
    }
  } catch (e) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Ошибка загрузки</td></tr>';
    console.error(e);
  }
}

window.addEventListener("load", () => loadTasks(false));
