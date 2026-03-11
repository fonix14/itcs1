function fmtDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("ru-RU");
  } catch (e) {
    return String(value);
  }
}

function isOverdue(value) {
  if (!value) return false;
  try {
    return new Date(value).getTime() < Date.now();
  } catch (e) {
    return false;
  }
}

let __allItems = [];
let __loading = false;

function renderTasks(items) {
  const tbody = document.querySelector("#tasksTable tbody");
  const count = document.getElementById("tasksCount");

  tbody.innerHTML = "";
  count.innerText = `Найдено задач: ${items.length}`;

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7">Нет данных</td></tr>`;
    return;
  }

  items.forEach((row) => {
    const overdue = isOverdue(row.sla_due_at || row.sla);
    const openUrl = `/ui/tasks/${row.id}`;
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td>${row.id ?? "—"}</td>
        <td>${row.portal_task_id ?? "—"}</td>
        <td>${row.store_no ?? "—"}</td>
        <td>${row.status ?? "—"}</td>
        <td class="${overdue ? "sla-overdue" : "sla-ok"}">${fmtDate(row.sla_due_at || row.sla)}</td>
        <td>${fmtDate(row.last_seen_at)}</td>
        <td><a class="btn" href="${openUrl}">Открыть</a></td>
      </tr>
      `
    );
  });
}

function applyFilter() {
  const q = document.getElementById("searchInput").value.trim().toLowerCase();

  if (!q) {
    renderTasks(__allItems);
    return;
  }

  const filtered = __allItems.filter((row) => {
    const portal = String(row.portal_task_id ?? "").toLowerCase();
    const store = String(row.store_no ?? "").toLowerCase();
    const status = String(row.status ?? "").toLowerCase();
    return portal.includes(q) || store.includes(q) || status.includes(q);
  });

  renderTasks(filtered);
}

async function loadTasks() {
  if (__loading || document.hidden) return;
  __loading = true;
  try {
    const resp = await fetch("/api/ops/tasks", { cache: "no-store" });
    const payload = await resp.json();
    __allItems = Array.isArray(payload) ? payload : [];
    applyFilter();
  } catch (e) {
    console.error("loadTasks failed", e);
  } finally {
    __loading = false;
  }
}

document.getElementById("refreshBtn").addEventListener("click", loadTasks);
document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(window.__searchTimer);
  window.__searchTimer = setTimeout(applyFilter, 250);
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) loadTasks();
});

loadTasks();
setInterval(loadTasks, 15000);
