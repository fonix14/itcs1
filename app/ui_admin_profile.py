from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth_ui import require_ui_dispatcher

router = APIRouter()


@router.get("/ui/admin/profile", response_class=HTMLResponse)
async def ui_admin_profile(request: Request):
    guard = require_ui_dispatcher(request)
    if not isinstance(guard, dict):
        return guard

    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Администратор</title>
  <link rel="stylesheet" href="/static/admin_profile.css?v=serverpanel1">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp1">
  <link rel="stylesheet" href="/static/responsive_global.css?v=resp-final">
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div>
        <div class="eyebrow">ITCS / ПРОФИЛЬ АДМИНИСТРАТОРА</div>
        <h1 style="font-size:32px;line-height:1.08;margin:0;">Администратор</h1>
        <div class="subline" style="font-size:14px;line-height:1.4;">Операционный профиль и контроль состояния сервера / API.</div>
      </div>
      <nav class="topbar-actions">
        <a class="btn" href="/ui/director">Главная</a>
        <a class="btn" href="/ui/director/dashboard">Операционный обзор</a>
        <a class="btn" href="/ui/tasks">Задачи</a>
        <a class="btn" href="/ui/admin/managers">Менеджеры</a>
        <a class="btn" href="/ui/dashboard">Дашборд диспетчера</a>
        <a class="btn primary" href="/ui/admin/profile">Админ</a>
        <a class="btn" href="/logout">Выход</a>
      </nav>
    </header>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Учетная запись</div>
        <div id="profileBox" class="profile-box">Загрузка...</div>
      </div>

      <div class="card">
        <div class="card-title">Состояние сервера</div>
        <div class="server-grid">
          <div class="metric-card">
            <div class="metric-label">CPU</div>
            <div class="metric-value" id="cpuUsage">—</div>
            <div class="metric-sub" id="cpuMeta">—</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">RAM</div>
            <div class="metric-value" id="ramUsage">—</div>
            <div class="metric-sub" id="ramMeta">—</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">DISK</div>
            <div class="metric-value" id="diskUsage">—</div>
            <div class="metric-sub" id="diskMeta">—</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">API</div>
            <div class="metric-value" id="apiStatus">—</div>
            <div class="metric-sub" id="apiMeta">—</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">DB</div>
            <div class="metric-value" id="dbStatus">—</div>
            <div class="metric-sub" id="dbMeta">—</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">UPTIME</div>
            <div class="metric-value" id="uptimeValue">—</div>
            <div class="metric-sub" id="uptimeMeta">—</div>
          </div>
        </div>
      </div>
    </section>

    <section class="kpi-grid">
      <div class="card kpi"><div class="label">Менеджеров</div><div class="value" id="kpiManagers">—</div></div>
      <div class="card kpi"><div class="label">Магазинов</div><div class="value" id="kpiStores">—</div></div>
      <div class="card kpi"><div class="label">Активных задач</div><div class="value" id="kpiTasks">—</div></div>
      <div class="card kpi"><div class="label">Импортов</div><div class="value" id="kpiUploads">—</div></div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="card-title">Техническая информация</div>
        <div id="techBox" class="profile-box">Загрузка...</div>
      </div>

      <div class="card">
        <div class="card-title">По ядрам CPU</div>
        <div id="cpuCoresBox" class="cpu-cores-box">Загрузка...</div>
      </div>
    </section>
  </div>

  <script>
    function esc(v) {
      return String(v ?? "—")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function badgeByPercent(value) {
      const n = Number(value || 0);
      if (n >= 90) return "danger";
      if (n >= 75) return "warn";
      return "ok";
    }

    function badgeByStatus(value) {
      const s = String(value || "").toLowerCase();
      if (s === "ok") return "ok";
      return "danger";
    }

    async function loadAdminProfile() {
      try {
        const [profileResp, serverResp] = await Promise.all([
          fetch("/api/admin/profile", { credentials: "same-origin" }),
          fetch("/api/admin/server/overview", { credentials: "same-origin" })
        ]);

        const profilePayload = await profileResp.json();
        const serverPayload = await serverResp.json();

        if (profilePayload.status !== "ok") {
          document.getElementById("profileBox").innerHTML = '<div class="error">Не удалось загрузить профиль</div>';
        } else {
          const p = profilePayload.data || {};
          document.getElementById("profileBox").innerHTML = `
            <div class="row"><span class="label">ФИО</span><span class="value">${esc(p.full_name)}</span></div>
            <div class="row"><span class="label">Email</span><span class="value">${esc(p.email)}</span></div>
            <div class="row"><span class="label">Роль</span><span class="value">${esc(p.role)}</span></div>
            <div class="row"><span class="label">ID</span><span class="value mono">${esc(p.user_id)}</span></div>
          `;
          document.getElementById("kpiManagers").textContent = p.managers_count ?? "—";
          document.getElementById("kpiStores").textContent = p.stores_count ?? "—";
          document.getElementById("kpiTasks").textContent = p.tasks_count ?? "—";
          document.getElementById("kpiUploads").textContent = p.uploads_count ?? "—";
        }

        if (serverPayload.status !== "ok") {
          document.getElementById("techBox").innerHTML = '<div class="error">Не удалось загрузить серверные метрики</div>';
          return;
        }

        const d = serverPayload.data || {};
        const cpu = d.cpu || {};
        const ram = d.ram || {};
        const disk = d.disk || {};
        const api = d.api || {};
        const db = d.db || {};
        const uptime = d.uptime || {};

        document.getElementById("cpuUsage").innerHTML = `<span class="status-badge ${badgeByPercent(cpu.usage_percent)}">${esc(cpu.usage_percent)}%</span>`;
        document.getElementById("cpuMeta").textContent = `${cpu.physical_cores ?? "—"} phys / ${cpu.logical_cores ?? "—"} log`;

        document.getElementById("ramUsage").innerHTML = `<span class="status-badge ${badgeByPercent(ram.usage_percent)}">${esc(ram.usage_percent)}%</span>`;
        document.getElementById("ramMeta").textContent = `${ram.used_gb ?? "—"} / ${ram.total_gb ?? "—"} GB`;

        document.getElementById("diskUsage").innerHTML = `<span class="status-badge ${badgeByPercent(disk.usage_percent)}">${esc(disk.usage_percent)}%</span>`;
        document.getElementById("diskMeta").textContent = `${disk.used_gb ?? "—"} / ${disk.total_gb ?? "—"} GB`;

        document.getElementById("apiStatus").innerHTML = `<span class="status-badge ${badgeByStatus(api.status)}">${esc(api.status)}</span>`;
        document.getElementById("apiMeta").textContent = `${api.response_ms ?? "—"} ms | PID ${api.process_pid ?? "—"}`;

        document.getElementById("dbStatus").innerHTML = `<span class="status-badge ${badgeByStatus(db.status)}">${esc(db.status)}</span>`;
        document.getElementById("dbMeta").textContent = db.error ? db.error : "Подключение к БД активно";

        document.getElementById("uptimeValue").textContent = uptime.uptime_human || "—";
        document.getElementById("uptimeMeta").textContent = uptime.boot_time || "—";

        document.getElementById("techBox").innerHTML = `
          <div class="row"><span class="label">Hostname</span><span class="value">${esc(d.hostname)}</span></div>
          <div class="row"><span class="label">Platform</span><span class="value">${esc(d.platform)}</span></div>
          <div class="row"><span class="label">Python</span><span class="value">${esc(d.python_version)}</span></div>
          <div class="row"><span class="label">API RSS</span><span class="value">${esc(api.process_rss_mb)} MB</span></div>
          <div class="row"><span class="label">Load Average</span><span class="value">${esc((cpu.load_avg || []).join(" / ") || "—")}</span></div>
          <div class="row"><span class="label">UTC time</span><span class="value">${esc(d.server_time_utc)}</span></div>
        `;

        const cores = Array.isArray(cpu.per_cpu_percent) ? cpu.per_cpu_percent : [];
        document.getElementById("cpuCoresBox").innerHTML = cores.length
          ? cores.map((v, i) => `
              <div class="cpu-core-row">
                <span>CPU ${i}</span>
                <div class="cpu-bar"><span class="cpu-bar-fill ${badgeByPercent(v)}" style="width:${Math.min(100, Number(v || 0))}%"></span></div>
                <strong>${esc(v)}%</strong>
              </div>
            `).join("")
          : '<div class="muted-line">Нет данных по ядрам</div>';

      } catch (e) {
        document.getElementById("profileBox").innerHTML = '<div class="error">Ошибка загрузки</div>';
        document.getElementById("techBox").innerHTML = `<div class="error">${esc(String(e))}</div>`;
      }
    }

    loadAdminProfile();
    setInterval(loadAdminProfile, 15000);
  </script>
</body>
</html>
    """)
