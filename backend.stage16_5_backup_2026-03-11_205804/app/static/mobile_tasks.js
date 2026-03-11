function formatDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString(); } catch (e) { return String(value); }
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

async function loadMobileTasks() {
  const q = (document.getElementById("q").value || "").trim().toLowerCase();
  const container = document.getElementById("tasks_container");
  container.innerHTML = "Загрузка...";

  try {
    const resp = await fetch("/api/mobile/tasks");
    const payload = await resp.json();
    if (payload.status !== "ok") throw new Error(payload.error || "load failed");

    let rows = payload.data || [];
    if (q) {
      rows = rows.filter(x =>
        String(x.portal_task_id || "").toLowerCase().includes(q) ||
        String(x.store_no || "").toLowerCase().includes(q)
      );
    }

    if (!rows.length) {
      container.innerHTML = "Нет задач";
      return;
    }

    container.innerHTML = "";
    for (const item of rows) {
      const a = document.createElement("a");
      a.className = "task";
      a.href = `/m/task/${item.id}`;
      a.innerHTML = `
        <div class="top">
          <div>
            <div class="id">Заявка ${item.portal_task_id ?? item.id}</div>
            <div class="store">Магазин: ${item.store_no ?? "—"}</div>
          </div>
          <div>${item.status ?? "—"}</div>
        </div>
        <div class="grid">
          <div>
            <div class="label">SLA</div>
            <div class="v">${renderSla(item.sla)}</div>
          </div>
          <div>
            <div class="label">Last seen</div>
            <div class="v">${formatDate(item.last_seen_at)}</div>
          </div>
        </div>
      `;
      container.appendChild(a);
    }
  } catch (e) {
    container.innerHTML = "Ошибка загрузки";
    console.error(e);
  }
}

window.addEventListener("load", loadMobileTasks);
