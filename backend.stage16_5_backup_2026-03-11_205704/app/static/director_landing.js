function fmtDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function fmtPercent(value) {
  if (value == null) return "—";
  return `${Number(value).toFixed(1)}%`;
}

function trustText(value) {
  const trust = (value || "UNKNOWN").toUpperCase();
  if (trust === "GREEN") return "GREEN";
  if (trust === "YELLOW") return "YELLOW";
  if (trust === "RED") return "RED";
  return "UNKNOWN";
}

async function loadDirectorLanding() {
  const resp = await fetch("/api/director/landing");
  const payload = await resp.json();

  if (payload.status !== "ok") {
    document.getElementById("heroSubtitle").innerText = payload.error || "Ошибка загрузки директорского экрана";
    return;
  }

  const data = payload.data || {};
  const hero = data.hero || {};
  const kpi = data.kpi || {};

  document.getElementById("heroTitle").innerText = hero.title || "Директорский экран платформы";
  document.getElementById("heroSubtitle").innerText = hero.subtitle || "—";

  document.getElementById("kpiActive").innerText = kpi.active_tasks ?? "—";
  document.getElementById("kpiOverdue").innerText = kpi.overdue_sla ?? "—";
  document.getElementById("kpiAnomalies").innerText = kpi.pending_anomalies ?? "—";
  document.getElementById("kpiTrust").innerText = trustText(kpi.trust_level);
  document.getElementById("kpiImport").innerText = fmtDate(kpi.last_import_at);
  document.getElementById("kpiInvalid").innerText = fmtPercent(kpi.invalid_ratio);

  const platformValueBox = document.getElementById("platformValueBox");
  platformValueBox.innerHTML = (data.platform_value || [])
    .slice(0, 2)
    .map(x => `<div class="hero-bullet">• ${x}</div>`)
    .join("");

  const modulesGrid = document.getElementById("modulesGrid");
  modulesGrid.innerHTML = "";
  (data.modules || []).forEach((item) => {
    const statusClass =
      item.status === "active" ? "module-active" :
      item.status === "planned" ? "module-planned" : "module-neutral";

    const href = item.route && item.route !== "#" ? item.route : "javascript:void(0)";
    modulesGrid.insertAdjacentHTML(
      "beforeend",
      `
      <a class="module-card ${statusClass}" href="${href}">
        <div class="module-tag">${item.tag || "Модуль"}</div>
        <div class="module-title">${item.title || "Модуль"}</div>
        <div class="module-text">${item.description || ""}</div>
      </a>
      `
    );
  });

  const roadmapBox = document.getElementById("roadmapBox");
  roadmapBox.innerHTML = "";
  (data.roadmap || []).forEach((row) => {
    const cls = row.status === "done" ? "roadmap-done" : "roadmap-next";
    roadmapBox.insertAdjacentHTML(
      "beforeend",
      `
      <div class="roadmap-item ${cls}">
        <div class="roadmap-stage">${row.stage}</div>
        <div class="roadmap-title">${row.title}</div>
      </div>
      `
    );
  });

  const valueList = document.getElementById("valueList");
  valueList.innerHTML = "";
  (data.platform_value || []).forEach((row) => {
    valueList.insertAdjacentHTML(
      "beforeend",
      `<div class="value-item">• ${row}</div>`
    );
  });
}

loadDirectorLanding().catch((e) => {
  document.getElementById("heroSubtitle").innerText = e.message || "Непредвиденная ошибка";
});
