async function loadCommandCenter() {
  const resp = await fetch("/api/command-center/overview");
  const payload = await resp.json();

  if (payload.status !== "ok") {
    return;
  }

  const data = payload.data || {};
  const kpi = data.kpi || {};
  const trust = data.trust || {};

  document.getElementById("kpiActive").innerText = kpi.active_tasks ?? "—";
  document.getElementById("kpiOverdue").innerText = kpi.overdue_sla ?? "—";
  document.getElementById("kpiInvalid").innerText =
    kpi.invalid_ratio != null ? `${Number(kpi.invalid_ratio).toFixed(1)}%` : "—";
  document.getElementById("kpiTrust").innerText = trust.trust_level ?? "—";

  const quickActions = document.getElementById("quickActions");
  quickActions.innerHTML = "";
  (data.quick_actions || []).forEach((item) => {
    const titleMap = {
      upload: "Загрузить Excel",
      tasks: "Открыть задачи",
      dashboard: "Открыть дашборд",
      mobile: "Мобильный вид"
    };
    const title = titleMap[item.code] || item.title || "Действие";
    quickActions.insertAdjacentHTML(
      "beforeend",
      `<a class="action-btn" href="${item.route_path}">${item.icon || ""} ${title}</a>`
    );
  });

  const modulesBox = document.getElementById("modulesBox");
  modulesBox.innerHTML = "";
  (data.modules || []).forEach((item) => {
    const nameMap = {
      supplier_tasks: "Заявки поставщика",
      imports: "Импорт Excel",
      dashboard: "Дашборд диспетчера",
      director: "Директорский дашборд"
    };
    const name = nameMap[item.code] || item.name || "Модуль";
    modulesBox.insertAdjacentHTML(
      "beforeend",
      `<a class="action-btn" href="${item.route_path}">${item.icon || ""} ${name}</a>`
    );
  });
}

loadCommandCenter().catch(console.error);
