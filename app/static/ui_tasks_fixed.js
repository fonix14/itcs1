function fmtDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString("ru-RU"); }
  catch { return String(value); }
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function slaPill(state, value) {
  const text = fmtDate(value);
  if (state === "red") return `<span class="pill pill-red">${text}</span>`;
  if (state === "yellow") return `<span class="pill pill-yellow">${text}</span>`;
  if (state === "green") return `<span class="pill pill-green">${text}</span>`;
  return `<span class="pill pill-gray">${text}</span>`;
}

function riskPill(value) {
  const v = String(value || "none");
  if (v === "overdue") return `<span class="pill pill-red">overdue</span>`;
  if (v === "warning") return `<span class="pill pill-yellow">warning</span>`;
  if (v === "normal") return `<span class="pill pill-green">normal</span>`;
  return `<span class="pill pill-gray">none</span>`;
}

function workBadge(value) {
  const v = String(value || "new");
  return `<span class="work-${v}">${esc(v)}</span>`;
}

let __allItems = [];
let __loading = false;

function calcRisk(row) {
  const work = String(row.internal_status || "new");
  if (work === "done") return "none";
  if (!row.sla_at) return "none";

  const now = new Date();
  const sla = new Date(row.sla_at);
  const diffMs = sla - now;

  if (diffMs < 0) return "overdue";
  if (diffMs <= 24 * 60 * 60 * 1000) return "warning";
  return "normal";
}

function renderManagerFilter(items) {
  const el = document.getElementById("managerFilter");
  const current = el.value;
  const names = [...new Set(items.map(x => (x.manager_name || "—")).filter(Boolean))].sort((a, b) => a.localeCompare(b, "ru"));
  el.innerHTML = `<option value="">Все менеджеры</option>` + names.map(name => `<option value="${esc(name)}">${esc(name)}</option>`).join("");
  if ([...el.options].some(o => o.value === current)) el.value = current;
}

function renderTaskSummary(summary, riskSummary) {
  document.getElementById("m_total").innerText = riskSummary.active_total ?? 0;
  document.getElementById("m_new").innerText = summary.new_count ?? 0;
  document.getElementById("m_in_progress").innerText = summary.in_progress_count ?? 0;
  document.getElementById("m_waiting").innerText = summary.waiting_count ?? 0;
  document.getElementById("m_done").innerText = summary.done_count ?? 0;
  document.getElementById("m_normal").innerText = riskSummary.normal_count ?? 0;
  document.getElementById("m_warning").innerText = riskSummary.warning_count ?? 0;
  document.getElementById("m_overdue").innerText = riskSummary.overdue_count ?? 0;
}

function renderTasks(items) {
  const tbody = document.querySelector("#tasksTable tbody");
  const count = document.getElementById("tasksCount");

  tbody.innerHTML = "";
  count.innerText = `Найдено задач: ${items.length}`;

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="9">Нет данных</td></tr>`;
    return;
  }

  items.forEach((row) => {
    const riskState = calcRisk(row);

    tbody.insertAdjacentHTML("beforeend", `
      <tr>
        <td>${esc(row.id)}</td>
        <td>${esc(row.portal_task_id || "—")}</td>
        <td>${esc(row.store_no || "—")}</td>
        <td>${esc(row.portal_status || "—")}</td>
        <td>${workBadge(row.internal_status)}</td>
        <td>${esc(row.manager_name || "—")}</td>
        <td>${riskPill(riskState)}</td>
        <td>${slaPill(row.sla_state, row.sla_at)}</td>
        <td>${fmtDate(row.last_seen_at)}</td>
      </tr>
    `);
  });
}

function renderRiskFeed(items) {
  const tbody = document.querySelector("#riskFeedTable tbody");
  tbody.innerHTML = "";

  const filtered = items.filter(x => ["warning", "overdue"].includes(x.risk_state)).slice(0, 20);

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="5">Нет задач под риском.</td></tr>`;
    return;
  }

  filtered.forEach((row) => {
    tbody.insertAdjacentHTML("beforeend", `
      <tr>
        <td>${esc(row.store_no || "—")}</td>
        <td>${esc(row.manager_name || "—")}</td>
        <td>${workBadge(row.internal_status)}</td>
        <td>${riskPill(row.risk_state)}</td>
        <td>${fmtDate(row.sla_at)}</td>
      </tr>
    `);
  });
}

function renderManagerLoad(items) {
  const tbody = document.querySelector("#managerLoadTable tbody");
  tbody.innerHTML = "";

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="4">Нет данных.</td></tr>`;
    return;
  }

  items.forEach((row) => {
    tbody.insertAdjacentHTML("beforeend", `
      <tr>
        <td>${esc(row.manager_name || "—")}</td>
        <td>${esc(row.active_count ?? 0)}</td>
        <td>${esc(row.overdue_count ?? 0)}</td>
        <td>${esc(row.warning_count ?? 0)}</td>
      </tr>
    `);
  });
}

function applyFilter() {
  const q = document.getElementById("searchInput").value.trim().toLowerCase();
  const manager = document.getElementById("managerFilter").value.trim().toLowerCase();
  const work = document.getElementById("workFilter").value.trim().toLowerCase();
  const risk = document.getElementById("riskFilter").value.trim().toLowerCase();

  const filtered = __allItems.filter((row) => {
    const riskState = calcRisk(row);

    const hay = [
      row.id, row.portal_task_id, row.store_no,
      row.portal_status, row.internal_status, row.manager_name
    ].map(x => String(x ?? "").toLowerCase()).join(" | ");

    return (!q || hay.includes(q))
      && (!manager || String(row.manager_name ?? "").toLowerCase() === manager)
      && (!work || String(row.internal_status ?? "").toLowerCase() === work)
      && (!risk || riskState === risk);
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
    renderManagerFilter(__allItems);
    applyFilter();
  } finally {
    __loading = false;
  }
}

async function loadTaskSummary() {
  const resp = await fetch("/api/ops/tasks/summary", { cache: "no-store" });
  return await resp.json();
}

async function loadRiskSummary() {
  const resp = await fetch("/api/ops/risk-summary", { cache: "no-store" });
  return await resp.json();
}

async function loadRiskFeed() {
  const resp = await fetch("/api/ops/risk-feed", { cache: "no-store" });
  const payload = await resp.json();
  renderRiskFeed(Array.isArray(payload) ? payload : []);
}

async function loadManagerLoad() {
  const resp = await fetch("/api/ops/manager-load", { cache: "no-store" });
  const payload = await resp.json();
  renderManagerLoad(Array.isArray(payload) ? payload : []);
}

async function reloadAll() {
  const [taskSummary, riskSummary] = await Promise.all([
    loadTaskSummary(),
    loadRiskSummary(),
    loadTasks(),
    loadRiskFeed(),
    loadManagerLoad(),
  ]).then(results => [results[0], results[1]]);

  renderTaskSummary(taskSummary, riskSummary);
}

async function runRiskScan() {
  const resp = await fetch("/api/ops/risk-scan", { method: "POST" });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка пересчёта рисков");
    return;
  }
  await reloadAll();
}

document.getElementById("refreshBtn").addEventListener("click", reloadAll);
document.getElementById("scanRiskBtn").addEventListener("click", runRiskScan);
document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(window.__searchTimer);
  window.__searchTimer = setTimeout(applyFilter, 200);
});
document.getElementById("managerFilter").addEventListener("change", applyFilter);
document.getElementById("workFilter").addEventListener("change", applyFilter);
document.getElementById("riskFilter").addEventListener("change", applyFilter);
document.addEventListener("visibilitychange", () => { if (!document.hidden) reloadAll(); });

reloadAll();
setInterval(reloadAll, 15000);
