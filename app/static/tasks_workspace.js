function fmtDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function isOverdue(value) {
  if (!value) return false;
  return new Date(value).getTime() < Date.now();
}

async function loadTasks() {
  const query = document.getElementById("searchInput").value.trim();
  const url = query ? `/api/tasks/ui?q=${encodeURIComponent(query)}` : "/api/tasks/ui";

  const resp = await fetch(url);
  const payload = await resp.json();

  const tbody = document.querySelector("#tasksTable tbody");
  tbody.innerHTML = "";

  const items = payload.data || [];
  document.getElementById("tasksCount").innerText = `Найдено задач: ${items.length}`;

  items.forEach((row) => {
    const overdue = isOverdue(row.sla_due_at);
    const slaClass = overdue ? "sla-overdue" : "sla-ok";

    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td>${row.portal_task_id ?? "—"}</td>
        <td>${row.store_no ?? "—"}</td>
        <td>${row.status ?? "—"}</td>
        <td class="${slaClass}">${fmtDate(row.sla_due_at)}</td>
        <td>${fmtDate(row.last_seen_at)}</td>
      </tr>
      `
    );
  });
}

document.getElementById("refreshBtn").addEventListener("click", loadTasks);
document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(window.__tasksSearchTimer);
  window.__tasksSearchTimer = setTimeout(loadTasks, 350);
});

loadTasks();
setInterval(loadTasks, 10000);
