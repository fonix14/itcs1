let currentFilter = "all";
let deferredPrompt = null;

function formatDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString(); } catch { return String(value); }
}

function renderSla(value) {
  if (!value) return '<span>—</span>';
  const now = new Date();
  const dt = new Date(value);
  const diffHours = (dt - now) / 1000 / 60 / 60;
  let cls = "sla-green";
  if (diffHours < 0) cls = "sla-red";
  else if (diffHours < 24) cls = "sla-yellow";
  return `<span class="${cls}">${formatDate(value)}</span>`;
}

function getActorId() {
  let value = localStorage.getItem("itcs_manager_uuid") || "";
  if (!value) {
    value = prompt("Введите UUID пользователя (X-User-Id):", "") || "";
    value = value.trim();
    if (value) localStorage.setItem("itcs_manager_uuid", value);
  }
  const input = document.getElementById("manager_uuid");
  if (input) input.value = value;
  return value;
}

function setActorId() {
  const input = document.getElementById("manager_uuid");
  const value = (input?.value || "").trim();
  if (value) localStorage.setItem("itcs_manager_uuid", value);
  else localStorage.removeItem("itcs_manager_uuid");
  loadTasks();
}

function apiHeaders() {
  const actorId = getActorId();
  const headers = { "X-User-Role": "manager" };
  if (actorId) headers["X-User-Id"] = actorId;
  return headers;
}

function setFilter(name, btn) {
  currentFilter = name;
  for (const el of document.querySelectorAll(".chip")) el.classList.remove("active");
  if (btn) btn.classList.add("active");
  loadTasks();
}

function filterRows(rows) {
  if (currentFilter === "accepted") return rows.filter(x => String(x.internal_status || x.status || "").toLowerCase() === "accepted");
  if (currentFilter === "open") return rows.filter(x => String(x.internal_status || "new").toLowerCase() !== "accepted");
  if (currentFilter === "overdue") {
    const now = new Date();
    return rows.filter(x => x.sla && new Date(x.sla) < now);
  }
  return rows;
}

function sortRows(rows) {
  const mode = document.getElementById("sort").value;
  if (mode === "new") {
    return [...rows].sort((a, b) => String(b.last_seen_at || "").localeCompare(String(a.last_seen_at || "")));
  }
  return [...rows].sort((a, b) => String(a.sla || "9999").localeCompare(String(b.sla || "9999")));
}

async function loadTasks() {
  const q = (document.getElementById("q").value || "").trim().toLowerCase();
  const container = document.getElementById("tasks_container");
  const meta = document.getElementById("meta");
  container.innerHTML = "Загрузка...";
  try {
    const resp = await fetch("/api/mobile/tasks", { headers: apiHeaders() });
    const payload = await resp.json();
    if (payload.status !== "ok") throw new Error(payload.error || "load failed");

    let rows = payload.data || [];
    rows = filterRows(rows);
    if (q) {
      rows = rows.filter(x =>
        String(x.portal_task_id || "").toLowerCase().includes(q) ||
        String(x.store_no || "").toLowerCase().includes(q)
      );
    }
    rows = sortRows(rows);
    meta.textContent = `Найдено заявок: ${rows.length}`;

    if (!rows.length) {
      container.innerHTML = '<div class="empty">Нет подходящих заявок</div>';
      return;
    }

    container.innerHTML = "";
    for (const item of rows) {
      const a = document.createElement("a");
      a.className = "task";
      a.href = `/m/task/${item.id}`;
      a.innerHTML = `
        <div class="task-top">
          <div>
            <div class="task-title">${item.portal_task_id ?? item.id}</div>
            <div class="task-store">Магазин: ${item.store_no ?? "—"}</div>
          </div>
          <div class="status">${item.internal_status === "accepted" ? "Принята" : (item.status ?? "—")}</div>
        </div>
        <div class="grid">
          <div>
            <div class="label">SLA</div>
            <div class="value">${renderSla(item.sla)}</div>
          </div>
          <div>
            <div class="label">Last seen</div>
            <div class="value">${formatDate(item.last_seen_at)}</div>
          </div>
        </div>
      `;
      container.appendChild(a);
    }
  } catch (e) {
    meta.textContent = "Ошибка";
    container.innerHTML = `<div class="error">${String(e)}</div>`;
    console.error(e);
  }
}

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
});

async function installPwa() {
  if (!deferredPrompt) {
    alert("На iPhone push работает только после 'Добавить на экран Домой'.");
    return;
  }
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(console.error);
  });
}

window.addEventListener("load", () => {
  getActorId();
  loadTasks();
});
