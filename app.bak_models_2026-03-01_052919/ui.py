from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])


@router.get("/ui", response_class=HTMLResponse)
async def ui_upload_page() -> str:
    # Простая страница: загрузка XLSX → POST /api/api/uploads через fetch()
    # Никаких зависимостей (Jinja2 не нужен).
    return """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>ITCS — Загрузка XLSX</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; max-width: 820px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; }
    label { display: block; font-size: 12px; color: #555; margin-bottom: 6px; }
    input, select, button { padding: 10px; border-radius: 10px; border: 1px solid #ccc; font-size: 14px; }
    button { cursor: pointer; }
    button.primary { border-color: #111; }
    pre { background: #0b1020; color: #e6edf3; padding: 12px; border-radius: 12px; overflow: auto; }
    .hint { color: #666; font-size: 13px; line-height: 1.35; }
    .ok { color: #0a7; font-weight: 600; }
    .bad { color: #c33; font-weight: 600; }
    a { color: #2457ff; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h2>ITCS — Загрузка XLSX</h2>

  <div class="card">
    <div class="row">
      <div style="flex: 1; min-width: 240px;">
        <label>X-User-Id (dispatcher UUID)</label>
        <input id="userId" placeholder="например: 00000000-0000-0000-0000-000000000001" style="width: 100%;">
      </div>
      <div style="min-width: 220px;">
        <label>X-User-Role</label>
        <select id="userRole" style="width: 100%;">
          <option value="dispatcher">dispatcher</option>
          <option value="manager">manager</option>
        </select>
      </div>
    </div>

    <div style="height: 12px;"></div>

    <div class="row">
      <div style="flex: 1; min-width: 240px;">
        <label>XLSX файл</label>
        <input id="file" type="file" accept=".xlsx" style="width: 100%;">
      </div>
      <div style="min-width: 220px; align-self: end;">
        <button class="primary" id="btnUpload">Загрузить</button>
      </div>
    </div>

    <div style="height: 12px;"></div>

    <div class="hint">
      <div>• Загрузка идёт в <code>/api/api/uploads</code> (как в Swagger).</div>
      <div>• Результат покажется ниже. После успешного импорта Stage 4 должен отправить дайджест в Matrix.</div>
      <div>• Swagger доступен: <a href="/docs" target="_blank">/docs</a></div>
    </div>
  </div>

  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
      <div><b>Результат</b> <span id="status"></span></div>
      <button id="btnHealth">Проверить Notifications Health</button>
    </div>
    <div style="height: 12px;"></div>
    <pre id="out">{}</pre>
  </div>

<script>
(function() {
  const $ = (id) => document.getElementById(id);
  const userIdEl = $("userId");
  const roleEl = $("userRole");
  const fileEl = $("file");
  const outEl = $("out");
  const statusEl = $("status");

  // restore saved
  userIdEl.value = localStorage.getItem("itcs_user_id") || "";
  roleEl.value = localStorage.getItem("itcs_user_role") || "dispatcher";

  function setStatus(text, ok) {
    statusEl.textContent = text ? ("— " + text) : "";
    statusEl.className = ok === true ? "ok" : ok === false ? "bad" : "";
  }

  async function upload() {
    try {
      setStatus("загрузка...", null);

      const f = fileEl.files && fileEl.files[0];
      if (!f) { setStatus("выбери XLSX", false); return; }

      const userId = userIdEl.value.trim();
      const role = roleEl.value;

      if (!userId) { setStatus("укажи X-User-Id", false); return; }

      localStorage.setItem("itcs_user_id", userId);
      localStorage.setItem("itcs_user_role", role);

      const fd = new FormData();
      fd.append("file", f);

      const resp = await fetch("/api/api/uploads", {
        method: "POST",
        headers: {
          "X-User-Id": userId,
          "X-User-Role": role
        },
        body: fd
      });

      const text = await resp.text();
      let json;
      try { json = JSON.parse(text); } catch { json = { raw: text }; }

      outEl.textContent = JSON.stringify(json, null, 2);

      if (resp.ok) setStatus("OK (импорт принят)", true);
      else setStatus("Ошибка (см. ответ)", false);

    } catch (e) {
      outEl.textContent = String(e && e.stack ? e.stack : e);
      setStatus("Ошибка JS/сети", false);
    }
  }

  async function health() {
    try {
      setStatus("health...", null);
      const userId = userIdEl.value.trim();
      const role = roleEl.value;

      if (!userId) { setStatus("укажи X-User-Id", false); return; }

      const resp = await fetch("/api/api/notifications/health", {
        headers: { "X-User-Id": userId, "X-User-Role": role }
      });
      const text = await resp.text();
      let json;
      try { json = JSON.parse(text); } catch { json = { raw: text }; }
      outEl.textContent = JSON.stringify(json, null, 2);
      setStatus(resp.ok ? "Health OK" : "Health error", resp.ok);
    } catch (e) {
      outEl.textContent = String(e && e.stack ? e.stack : e);
      setStatus("Ошибка health", false);
    }
  }

  $("btnUpload").addEventListener("click", upload);
  $("btnHealth").addEventListener("click", health);
})();
</script>
</body>
</html>
"""
