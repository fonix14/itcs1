function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value ?? "—";
}

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch (e) {
    return String(value);
  }
}

function renderWarnings(items) {
  const list = document.getElementById("warnings");
  if (!list) return;
  list.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.className = "ok";
    li.textContent = "Проблем не обнаружено";
    list.appendChild(li);
    return;
  }

  for (const item of items) {
    const li = document.createElement("li");
    li.className = item.includes("CRITICAL") || item.includes("NO_UPLOAD") ? "bad" : "warn";
    li.textContent = item;
    list.appendChild(li);
  }
}

function renderTrust(level) {
  const dot = document.getElementById("trust_dot");
  const text = document.getElementById("trust_text");
  if (!dot || !text) return;
  dot.className = "dot " + (level || "RED");
  text.textContent = level || "RED";
}

function renderManagerWorkload(items) {
  const body = document.getElementById("manager_workload_body");
  if (!body) return;
  body.innerHTML = "";

  if (!items || items.length === 0) {
    body.innerHTML = '<tr><td colspan="4" class="muted">Нет данных</td></tr>';
    return;
  }

  for (const item of items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.manager_name ?? "—"}</td>
      <td>${item.active_tasks ?? 0}</td>
      <td>${item.overdue_tasks ?? 0}</td>
      <td>${item.risk_24h_tasks ?? 0}</td>
    `;
    body.appendChild(tr);
  }
}

async function loadDashboard() {
  try {
    const [healthResp, slaResp] = await Promise.all([
      fetch("/api/dashboard/health"),
      fetch("/api/dashboard/sla")
    ]);

    const healthPayload = await healthResp.json();
    const slaPayload = await slaResp.json();

    if (healthPayload.status !== "ok") {
      throw new Error(healthPayload.error || "Health API error");
    }
    if (slaPayload.status !== "ok") {
      throw new Error(slaPayload.error || "SLA API error");
    }

    const d = healthPayload.data || {};
    const s = slaPayload.data || {};

    setText("tasks_total", d.tasks_total ?? 0);
    setText("uploads_total", d.uploads_total ?? 0);
    setText("open_anomalies", d.open_anomalies ?? 0);
    setText("critical_open_anomalies", d.critical_open_anomalies ?? 0);
    setText("invalid_percent", (d.invalid_percent ?? 0) + "%");
    setText("last_upload_at", formatDate(d.last_upload_at));
    setText("overdue_tasks", s.overdue_tasks ?? 0);
    setText("risk_24h_tasks", s.risk_24h_tasks ?? 0);

    renderTrust(d.trust_level);
    renderWarnings(d.warnings || []);
    renderManagerWorkload(s.manager_workload || []);
  } catch (e) {
    renderTrust("RED");
    renderWarnings(["DASHBOARD_LOAD_FAILED"]);
    console.error(e);
  }
}

window.addEventListener("load", loadDashboard);
