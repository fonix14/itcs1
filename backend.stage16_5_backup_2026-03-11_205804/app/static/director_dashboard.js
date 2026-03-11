function fmtDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function fmtPercent(value) {
  if (value == null) return "—";
  return `${Number(value).toFixed(1)}%`;
}

function setTrustBadge(level) {
  const badge = document.getElementById("trustBadge");
  const value = document.getElementById("kpiTrust");

  const trust = (level || "UNKNOWN").toUpperCase();

  badge.className = "trust-badge";
  value.className = "value trust-value";

  if (trust === "GREEN") {
    badge.classList.add("trust-green");
    value.classList.add("trust-green-text");
    badge.innerText = "GREEN";
  } else if (trust === "YELLOW") {
    badge.classList.add("trust-yellow");
    value.classList.add("trust-yellow-text");
    badge.innerText = "YELLOW";
  } else if (trust === "RED") {
    badge.classList.add("trust-red");
    value.classList.add("trust-red-text");
    badge.innerText = "RED";
  } else {
    badge.classList.add("trust-unknown");
    badge.innerText = "UNKNOWN";
  }

  value.innerText = trust;
}

function renderRiskBanner(kpi) {
  const banner = document.getElementById("riskBanner");
  const trust = (kpi.trust_level || "UNKNOWN").toUpperCase();
  const overdue = Number(kpi.overdue_sla || 0);
  const anomalies = Number(kpi.pending_anomalies || 0);

  let text = "";
  let cls = "risk-banner hidden";

  if (trust === "RED") {
    text = `Критическое состояние данных: уровень доверия RED. Просрочено по SLA: ${overdue}, аномалий в работе: ${anomalies}.`;
    cls = "risk-banner risk-red";
  } else if (trust === "YELLOW") {
    text = `Система требует внимания: уровень доверия YELLOW. Просрочено по SLA: ${overdue}, аномалий в работе: ${anomalies}.`;
    cls = "risk-banner risk-yellow";
  } else if (overdue > 0) {
    text = `Есть просроченные задачи по SLA: ${overdue}. Требуется контроль.`;
    cls = "risk-banner risk-blue";
  }

  banner.className = cls;
  banner.innerText = text;
}

function renderAttention(items) {
  const box = document.getElementById("attentionGrid");
  box.innerHTML = "";

  if (!items || !items.length) {
    box.innerHTML = `<div class="attention-empty">Критичных сигналов не обнаружено.</div>`;
    return;
  }

  items.forEach((item) => {
    const level = item.level || "ok";
    box.insertAdjacentHTML(
      "beforeend",
      `
      <div class="attention-card attention-${level}">
        <div class="attention-title">${item.title || "Сигнал"}</div>
        <div class="attention-text">${item.text || ""}</div>
      </div>
      `
    );
  });
}

function renderMiniChart(items) {
  const box = document.getElementById("uploadsMiniChart");
  box.innerHTML = "";

  if (!items || !items.length) {
    box.innerHTML = `<div class="attention-empty">Нет данных за последние 7 дней.</div>`;
    return;
  }

  const maxRows = Math.max(...items.map(x => Number(x.total_rows || 0)), 1);

  items.forEach((row) => {
    const totalRows = Number(row.total_rows || 0);
    const invalidRatio = Number(row.avg_invalid_ratio || 0);
    const width = Math.max(8, Math.round((totalRows / maxRows) * 100));

    box.insertAdjacentHTML(
      "beforeend",
      `
      <div class="mini-chart-row">
        <div class="mini-chart-label">${row.day_label || "—"}</div>
        <div class="mini-chart-bar-wrap">
          <div class="mini-chart-bar" style="width:${width}%"></div>
        </div>
        <div class="mini-chart-meta">
          <span>${totalRows} строк</span>
          <span>${invalidRatio.toFixed(1)}%</span>
        </div>
      </div>
      `
    );
  });
}

async function loadDirectorDashboard() {
  const resp = await fetch("/api/director/dashboard");
  const payload = await resp.json();

  if (payload.status !== "ok") {
    document.getElementById("summaryBox").innerText = payload.error || "Ошибка загрузки дашборда";
    return;
  }

  const data = payload.data || {};
  const kpi = data.kpi || {};
  const latestImport = data.latest_import || {};
  const todayRisk = data.today_risk || {};
  const weekMetrics = data.week_metrics || {};

  document.getElementById("kpiActive").innerText = kpi.active_tasks ?? "—";
  document.getElementById("kpiOverdue").innerText = kpi.overdue_sla ?? "—";
  document.getElementById("kpiInvalid").innerText = fmtPercent(kpi.invalid_ratio);
  document.getElementById("kpiAnomalies").innerText = kpi.pending_anomalies ?? "—";
  document.getElementById("kpiImport").innerText = fmtDate(latestImport.uploaded_at);

  document.getElementById("generatedAtLine").innerText = `Обновлено: ${fmtDate(data.generated_at)}`;

  document.getElementById("todayOverdue").innerText = todayRisk.overdue_sla ?? "—";
  document.getElementById("todayAnomalies").innerText = todayRisk.pending_anomalies ?? "—";
  document.getElementById("todayActive").innerText = todayRisk.active_tasks ?? "—";

  document.getElementById("weekUploads").innerText = weekMetrics.uploads_count ?? "—";
  document.getElementById("weekRows").innerText = weekMetrics.total_rows ?? "—";
  document.getElementById("weekInvalidRows").innerText = weekMetrics.invalid_rows ?? "—";
  document.getElementById("weekInvalidAvg").innerText = fmtPercent(weekMetrics.avg_invalid_ratio);

  setTrustBadge(kpi.trust_level);
  renderRiskBanner(kpi);

  document.getElementById("summaryBox").innerText =
    data.exec_summary || "Нет управленческой сводки.";

  renderAttention(data.attention_items || []);
  renderMiniChart(data.uploads_daily || []);

  const storesBody = document.querySelector("#storesTable tbody");
  storesBody.innerHTML = "";
  (data.top_stores || []).forEach((row, index) => {
    const rowClass = index < 3 ? "top-risk-row" : "";
    storesBody.insertAdjacentHTML(
      "beforeend",
      `<tr class="${rowClass}"><td>${row.store_no ?? "—"}</td><td>${row.open_tasks ?? 0}</td></tr>`
    );
  });

  const managersBody = document.querySelector("#managersTable tbody");
  managersBody.innerHTML = "";
  (data.manager_load || []).forEach((row) => {
    managersBody.insertAdjacentHTML(
      "beforeend",
      `<tr><td>${row.full_name ?? "—"}</td><td>${row.open_tasks ?? 0}</td></tr>`
    );
  });

  const uploadsBody = document.querySelector("#uploadsTable tbody");
  uploadsBody.innerHTML = "";
  (data.latest_uploads || []).forEach((row) => {
    uploadsBody.insertAdjacentHTML(
      "beforeend",
      `<tr>
        <td>${row.original_filename ?? "—"}</td>
        <td>${row.profile_code ?? "—"}</td>
        <td>${fmtDate(row.uploaded_at)}</td>
        <td>${fmtPercent(row.invalid_ratio)}</td>
      </tr>`
    );
  });
}

loadDirectorDashboard().catch((e) => {
  const el = document.getElementById("summaryBox");
  if (el) el.innerText = e.message || "Непредвиденная ошибка дашборда";
});
