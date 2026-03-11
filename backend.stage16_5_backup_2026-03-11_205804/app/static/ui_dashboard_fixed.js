async function loadDashboard() {
  const [healthResp, dashboardResp] = await Promise.all([
    fetch("/api/dashboard/health"),
    fetch("/api/director/dashboard")
  ]);

  const healthPayload = await healthResp.json();
  const dashboardPayload = await dashboardResp.json();

  if (dashboardPayload.status !== "ok") {
    document.getElementById("healthSummary").innerText = dashboardPayload.error || "Ошибка загрузки";
    return;
  }

  const d = dashboardPayload.data || {};
  const kpi = d.kpi || {};

  document.getElementById("kpiTasks").innerText = kpi.active_tasks ?? "—";
  document.getElementById("kpiUploads").innerText = (d.latest_uploads || []).length ?? "—";
  document.getElementById("kpiAnomalies").innerText = kpi.pending_anomalies ?? "—";
  document.getElementById("kpiInvalid").innerText =
    kpi.invalid_ratio != null ? `${Number(kpi.invalid_ratio).toFixed(1)}%` : "—";
  document.getElementById("kpiOverdue").innerText = kpi.overdue_sla ?? "—";
  document.getElementById("kpiRisk24").innerText = "—";

  let trustText = "Health не определён";
  if (healthPayload.status === "ok" && healthPayload.data) {
    const h = healthPayload.data;
    trustText = `Trust level: ${h.trust_level ?? "—"}\nПоследний расчёт: ${h.calculated_at ?? "—"}`;
  }

  document.getElementById("healthSummary").innerText = trustText;

  const warnings = [];
  if ((kpi.overdue_sla ?? 0) > 0) warnings.push("SLA_OVERDUE_PRESENT");
  if ((kpi.pending_anomalies ?? 0) > 0) warnings.push("OPEN_ANOMALIES_PRESENT");
  if ((kpi.invalid_ratio ?? 0) > 20) warnings.push("INVALID_RATIO_OVER_20");

  document.getElementById("warningsBox").innerText = warnings.length ? warnings.join("\n") : "Активных предупреждений нет";

  const tbody = document.querySelector("#managerLoadTable tbody");
  tbody.innerHTML = "";
  (d.manager_load || []).forEach((row) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td>${row.full_name ?? "—"}</td>
        <td>${row.open_tasks ?? 0}</td>
        <td>—</td>
        <td>—</td>
      </tr>
      `
    );
  });
}

loadDashboard().catch((e) => {
  document.getElementById("healthSummary").innerText = e.message || "Ошибка";
});
