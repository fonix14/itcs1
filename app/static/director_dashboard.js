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

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function trustClass(level) {
  const t = String(level || "").toUpperCase();
  if (t === "GREEN") return "trust-green";
  if (t === "YELLOW") return "trust-yellow";
  if (t === "RED") return "trust-red";
  return "trust-unknown";
}

async function loadDirectorDashboard() {
  const app = document.getElementById("directorDashboardApp");
  if (!app) return;

  app.innerHTML = "Загрузка...";

  try {
    const resp = await fetch("/api/director/dashboard", { credentials: "same-origin" });
    const payload = await resp.json();

    if (payload.status !== "ok") {
      app.innerHTML = `<div class="card">Ошибка загрузки: ${esc(payload.error || "unknown error")}</div>`;
      return;
    }

    const data = payload.data || {};
    const kpi = data.kpi || {};
    const latestImport = data.latest_import || {};
    const todayRisk = data.today_risk || {};
    const weekMetrics = data.week_metrics || {};
    const attention = Array.isArray(data.attention_items) ? data.attention_items : [];
    const topStores = Array.isArray(data.top_stores) ? data.top_stores : [];
    const managerLoad = Array.isArray(data.manager_load) ? data.manager_load : [];
    const latestUploads = Array.isArray(data.latest_uploads) ? data.latest_uploads : [];

    app.innerHTML = `
      <style>
        .dd-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:20px}
        .dd-grid-2{display:grid;grid-template-columns:1.2fr 1fr;gap:16px;margin-top:16px}
        .dd-card{
          background:rgba(15,27,49,.94);
          border:1px solid #223252;
          border-radius:18px;
          padding:18px;
          box-shadow:0 14px 40px rgba(0,0,0,.22);
        }
        .dd-title{font-size:15px;font-weight:700;margin-bottom:12px}
        .dd-kpi-label{color:#93a4bf;font-size:13px;margin-bottom:8px}
        .dd-kpi-value{font-size:30px;font-weight:800}
        .trust-green{color:#86efac}
        .trust-yellow{color:#fde68a}
        .trust-red{color:#fca5a5}
        .trust-unknown{color:#cbd5e1}
        .dd-table{width:100%;border-collapse:collapse}
        .dd-table th,.dd-table td{padding:10px 8px;border-bottom:1px solid rgba(34,50,82,.75);text-align:left;font-size:14px}
        .dd-table th{color:#93a4bf}
        .dd-note{padding:10px 12px;border:1px solid #223252;border-radius:12px;background:rgba(20,35,61,.65);margin-bottom:10px}
        .dd-muted{color:#93a4bf;font-size:13px}
        @media (max-width:1100px){
          .dd-grid{grid-template-columns:1fr 1fr}
          .dd-grid-2{grid-template-columns:1fr}
        }
        @media (max-width:700px){
          .dd-grid{grid-template-columns:1fr}
        }
      </style>

      <div class="dd-card">
        <div class="dd-title">Управленческая сводка</div>
        <div>${esc(data.exec_summary || "Нет управленческой сводки.")}</div>
        <div class="dd-muted" style="margin-top:10px">Обновлено: ${esc(fmtDate(data.generated_at))}</div>
      </div>

      <div class="dd-grid">
        <div class="dd-card">
          <div class="dd-kpi-label">Активные задачи</div>
          <div class="dd-kpi-value">${esc(kpi.active_tasks ?? "—")}</div>
        </div>
        <div class="dd-card">
          <div class="dd-kpi-label">Просрочено по SLA</div>
          <div class="dd-kpi-value">${esc(kpi.overdue_sla ?? "—")}</div>
        </div>
        <div class="dd-card">
          <div class="dd-kpi-label">Открытые аномалии</div>
          <div class="dd-kpi-value">${esc(kpi.pending_anomalies ?? "—")}</div>
        </div>
        <div class="dd-card">
          <div class="dd-kpi-label">Уровень доверия</div>
          <div class="dd-kpi-value ${trustClass(kpi.trust_level)}">${esc(kpi.trust_level || "UNKNOWN")}</div>
        </div>
      </div>

      <div class="dd-grid-2">
        <div class="dd-card">
          <div class="dd-title">Ключевые сигналы</div>
          ${attention.length
            ? attention.map(x => `<div class="dd-note"><strong>${esc(x.title || "Сигнал")}</strong><br>${esc(x.text || "")}</div>`).join("")
            : `<div class="dd-muted">Критичных сигналов не обнаружено.</div>`}
        </div>

        <div class="dd-card">
          <div class="dd-title">Последний импорт</div>
          <div class="dd-note"><strong>Файл:</strong> ${esc(latestImport.original_filename || "—")}</div>
          <div class="dd-note"><strong>Профиль:</strong> ${esc(latestImport.profile_code || "—")}</div>
          <div class="dd-note"><strong>Дата:</strong> ${esc(fmtDate(latestImport.uploaded_at))}</div>
          <div class="dd-note"><strong>Invalid %:</strong> ${esc(fmtPercent(latestImport.invalid_ratio))}</div>
        </div>
      </div>

      <div class="dd-grid-2">
        <div class="dd-card">
          <div class="dd-title">Нагрузка по менеджерам</div>
          <table class="dd-table">
            <thead><tr><th>Менеджер</th><th>Открытых задач</th></tr></thead>
            <tbody>
              ${managerLoad.length
                ? managerLoad.map(r => `<tr><td>${esc(r.full_name || "—")}</td><td>${esc(r.open_tasks ?? 0)}</td></tr>`).join("")
                : `<tr><td colspan="2">Нет данных</td></tr>`}
            </tbody>
          </table>
        </div>

        <div class="dd-card">
          <div class="dd-title">Топ магазинов по риску</div>
          <table class="dd-table">
            <thead><tr><th>Магазин</th><th>Открытых задач</th></tr></thead>
            <tbody>
              ${topStores.length
                ? topStores.map(r => `<tr><td>${esc(r.store_no || "—")}</td><td>${esc(r.open_tasks ?? 0)}</td></tr>`).join("")
                : `<tr><td colspan="2">Нет данных</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>

      <div class="dd-grid-2">
        <div class="dd-card">
          <div class="dd-title">Риски на сейчас</div>
          <div class="dd-note"><strong>Активных задач:</strong> ${esc(todayRisk.active_tasks ?? "—")}</div>
          <div class="dd-note"><strong>Просрочено SLA:</strong> ${esc(todayRisk.overdue_sla ?? "—")}</div>
          <div class="dd-note"><strong>Открытых аномалий:</strong> ${esc(todayRisk.pending_anomalies ?? "—")}</div>
          <div class="dd-note"><strong>Trust level:</strong> ${esc(todayRisk.trust_level ?? "—")}</div>
        </div>

        <div class="dd-card">
          <div class="dd-title">Метрики за 7 дней</div>
          <div class="dd-note"><strong>Импортов:</strong> ${esc(weekMetrics.uploads_count ?? "—")}</div>
          <div class="dd-note"><strong>Всего строк:</strong> ${esc(weekMetrics.total_rows ?? "—")}</div>
          <div class="dd-note"><strong>Невалидных строк:</strong> ${esc(weekMetrics.invalid_rows ?? "—")}</div>
          <div class="dd-note"><strong>Средний invalid %:</strong> ${esc(fmtPercent(weekMetrics.avg_invalid_ratio))}</div>
        </div>
      </div>

      <div class="dd-card" style="margin-top:16px">
        <div class="dd-title">Последние загрузки</div>
        <table class="dd-table">
          <thead>
            <tr>
              <th>Файл</th>
              <th>Профиль</th>
              <th>Дата</th>
              <th>Invalid %</th>
            </tr>
          </thead>
          <tbody>
            ${latestUploads.length
              ? latestUploads.map(r => `
                <tr>
                  <td>${esc(r.original_filename || "—")}</td>
                  <td>${esc(r.profile_code || "—")}</td>
                  <td>${esc(fmtDate(r.uploaded_at))}</td>
                  <td>${esc(fmtPercent(r.invalid_ratio))}</td>
                </tr>
              `).join("")
              : `<tr><td colspan="4">Нет данных</td></tr>`}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    app.innerHTML = `<div class="dd-card">Непредвиденная ошибка: ${esc(e.message || String(e))}</div>`;
    console.error(e);
  }
}

window.addEventListener("load", loadDirectorDashboard);
