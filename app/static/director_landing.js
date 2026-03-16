function fmtDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("ru-RU");
  } catch {
    return String(value);
  }
}

function fmtPercent(value) {
  if (value == null) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return `${n.toFixed(1)}%`;
}

function trustText(value) {
  const trust = String(value || "UNKNOWN").toUpperCase();
  if (["GREEN", "YELLOW", "RED"].includes(trust)) return trust;
  return "UNKNOWN";
}

function safeSetText(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerText = value ?? "—";
}

function safeSetHTML(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = value ?? "";
}

async function loadDirectorLanding() {
  try {
    const resp = await fetch("/api/director/landing", { credentials: "same-origin" });
    const payload = await resp.json();

    if (payload.status !== "ok") {
      safeSetText("heroSubtitle", payload.error || "Ошибка загрузки командного центра");
      return;
    }

    const data = payload.data || {};
    const hero = data.hero || {};
    const kpi = data.kpi || {};
    const platformValue = Array.isArray(data.platform_value) ? data.platform_value : [];
    const roadmap = Array.isArray(data.roadmap) ? data.roadmap : [];

    safeSetText("heroSubtitle", hero.subtitle || "Единая точка входа для контроля задач и рисков.");
    safeSetText("kpiTasks", kpi.active_tasks ?? "—");
    safeSetText("kpiOverdue", kpi.overdue_sla ?? "—");
    safeSetText("kpiAnomalies", kpi.pending_anomalies ?? "—");
    safeSetText("kpiTrust", trustText(kpi.trust_level));
    safeSetText("kpiImport", fmtDate(kpi.last_import_at));
    safeSetText("kpiInvalid", fmtPercent(kpi.invalid_ratio));

    safeSetHTML(
      "effectBox",
      platformValue.length
        ? platformValue.slice(0, 2).map(x => `<div class="value-item">• ${x}</div>`).join("")
        : "Нет данных"
    );

    safeSetHTML(
      "roadmapBox",
      roadmap.length
        ? roadmap.map(x => `
            <div class="value-item">
              <strong>${x.stage || "Stage"}</strong> — ${x.title || "—"}
            </div>
          `).join("")
        : "Нет roadmap данных"
    );

    safeSetHTML(
      "leaderBox",
      platformValue.length
        ? platformValue.map(x => `<div class="value-item">• ${x}</div>`).join("")
        : "Нет данных"
    );

  } catch (e) {
    safeSetText("heroSubtitle", e.message || "Непредвиденная ошибка");
    console.error(e);
  }
}

window.addEventListener("load", loadDirectorLanding);
