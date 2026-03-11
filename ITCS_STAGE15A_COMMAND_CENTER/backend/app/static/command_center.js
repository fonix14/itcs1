async function loadCommandCenter() {
  const trustBadge = document.getElementById("trustBadge");
  const trustMeta = document.getElementById("trustMeta");
  const summaryTitle = document.getElementById("summaryTitle");
  const summaryText = document.getElementById("summaryText");
  const modulesGrid = document.getElementById("modulesGrid");
  const quickActions = document.getElementById("quickActions");

  try {
    const resp = await fetch("/api/command-center/overview", { cache: "no-store" });
    const payload = await resp.json();

    if (payload.status !== "ok") {
      throw new Error(payload.error || "Command Center API error");
    }

    const data = payload.data || {};
    const kpi = data.kpi || {};
    const trust = data.trust || {};
    const upload = data.latest_upload || {};
    const modules = data.modules || [];
    const actions = data.quick_actions || [];
    const summary = data.summary || {};

    document.getElementById("kpiActiveTasks").textContent = num(kpi.active_tasks);
    document.getElementById("kpiOverdueSla").textContent = num(kpi.overdue_sla);
    document.getElementById("kpiAnomalies").textContent = num(kpi.pending_anomalies);
    document.getElementById("kpiInvalidRatio").textContent = fmtPercent(kpi.invalid_ratio);

    const badge = trust.badge || { label: "UNKNOWN", tone: "slate" };
    trustBadge.textContent = badge.label || "UNKNOWN";
    trustBadge.className = `badge ${badge.tone || "slate"}`;

    const trustTime = trust.calculated_at ? formatDateTime(trust.calculated_at) : "—";
    const noImportHours = trust.no_import_duration_hours != null ? `${trust.no_import_duration_hours} ч` : "—";
    const pendingAnomalies = trust.pending_anomalies != null ? trust.pending_anomalies : num(kpi.pending_anomalies);
    trustMeta.textContent = `Последний расчёт: ${trustTime}. No import: ${noImportHours}. Pending anomalies: ${pendingAnomalies}.`;

    document.getElementById("lastUploadFilename").textContent = upload.filename || "—";
    document.getElementById("lastUploadProfile").textContent = upload.profile_code || "—";
    document.getElementById("lastUploadTime").textContent = upload.uploaded_at ? formatDateTime(upload.uploaded_at) : "—";
    document.getElementById("lastUploadInvalid").textContent = fmtPercent(upload.invalid_ratio);

    summaryTitle.textContent = summary.title || "Краткая управленческая сводка";
    summaryText.textContent = summary.text || "Данных пока нет.";

    quickActions.innerHTML = "";
    actions.forEach((item) => quickActions.appendChild(renderAction(item)));

    modulesGrid.innerHTML = "";
    modules.forEach((item) => modulesGrid.appendChild(renderModule(item)));
  } catch (err) {
    summaryTitle.textContent = "Ошибка загрузки";
    summaryText.textContent = err.message || String(err);
    trustBadge.textContent = "ERROR";
    trustBadge.className = "badge red";
    trustMeta.textContent = "Не удалось получить overview.";
  }
}

function renderAction(item) {
  const a = document.createElement("a");
  a.className = "action-btn";
  a.href = item.route_path || "#";
  a.innerHTML = `<span class="action-icon">${escapeHtml(item.icon || "→")}</span><span>${escapeHtml(item.title || item.code || "Action")}</span>`;
  return a;
}

function renderModule(item) {
  const a = document.createElement("a");
  a.className = "module-card";
  a.href = item.route_path || "#";
  a.innerHTML = `
    <div class="module-icon">${escapeHtml(item.icon || "□")}</div>
    <div class="module-title">${escapeHtml(item.name || item.code || "Module")}</div>
    <div class="module-desc">${escapeHtml(item.description || "")}</div>
  `;
  return a;
}

function num(v) {
  return v == null ? "0" : String(v);
}

function fmtPercent(v) {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return `${n.toFixed(1)}%`;
}

function formatDateTime(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("ru-RU");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

document.addEventListener("DOMContentLoaded", loadCommandCenter);
