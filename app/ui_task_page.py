from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth_ui import require_ui_manager_or_dispatcher

router = APIRouter()


def render_task_html(task_id: str, back_path: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карточка заявки</title>
<link rel="stylesheet" href="/static/responsive_global.css?v=resp3">
<style>
body {{
    margin:0;
    background:radial-gradient(circle at top,#0a1930,#040b16);
    font-family:Arial,sans-serif;
    color:white;
}}
.container {{
    max-width:1280px;
    margin:32px auto;
    padding:0 20px 40px;
}}
.topline {{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:16px;
    margin-bottom:20px;
}}
.back {{
    display:inline-block;
    color:#cfe0ff;
    text-decoration:none;
    margin-bottom:18px;
}}
.title {{
    font-size:32px;
    font-weight:800;
    line-height:1.05;
    margin:0 0 8px;
}}
.sub {{
    color:#9db2d1;
    margin:0;
}}
.grid {{
    display:grid;
    grid-template-columns:1.05fr .95fr;
    gap:18px;
}}
.card {{
    background:#0f1b31;
    border:1px solid #223252;
    border-radius:20px;
    padding:20px;
    box-shadow:0 14px 40px rgba(0,0,0,.22);
}}
.card-title {{
    font-size:15px;
    font-weight:700;
    margin-bottom:14px;
}}
.rows {{
    display:grid;
    gap:10px;
}}
.row {{
    display:grid;
    grid-template-columns:180px 1fr;
    gap:16px;
    padding:10px 0;
    border-bottom:1px solid rgba(34,50,82,.75);
}}
.label {{
    color:#9db2d1;
}}
.value {{
    font-size:15px;
    font-weight:600;
    word-break:break-word;
}}
.meta-badges {{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
    margin-top:12px;
}}
.badge {{
    padding:6px 10px;
    border-radius:999px;
    border:1px solid #223252;
    background:rgba(20,35,61,.65);
    color:#d8e5fb;
    font-size:12px;
}}
.comment-box {{
    display:grid;
    gap:12px;
}}
textarea {{
    width:100%;
    min-height:130px;
    resize:vertical;
    background:#081224;
    color:white;
    border:1px solid #23385e;
    border-radius:12px;
    padding:12px;
    box-sizing:border-box;
}}
.actions {{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px;
}}
.btn {{
    display:inline-block;
    padding:12px 16px;
    background:#0f1b31;
    border:1px solid #223252;
    color:white;
    border-radius:12px;
    text-decoration:none;
    cursor:pointer;
    text-align:center;
}}
.btn.primary {{
    background:#4f8cff;
    border-color:#4f8cff;
}}
.comments {{
    display:grid;
    gap:12px;
    margin-top:18px;
}}
.comment {{
    border:1px solid #223252;
    border-radius:14px;
    padding:14px;
    background:rgba(20,35,61,.65);
}}
.comment-head {{
    display:flex;
    justify-content:space-between;
    gap:12px;
    margin-bottom:8px;
    color:#9db2d1;
    font-size:12px;
}}
.comment-role {{
    display:inline-block;
    padding:4px 8px;
    border-radius:999px;
    background:rgba(79,140,255,.14);
    border:1px solid rgba(79,140,255,.28);
    color:#cfe0ff;
    margin-left:8px;
}}
.payload {{
    white-space:pre-wrap;
    word-break:break-word;
    color:#d8e5fb;
    font-family:ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size:12px;
}}
.empty {{
    color:#9db2d1;
}}
.error {{
    background:#4a1620;
    color:#ffd7de;
    border:1px solid #6b2432;
    padding:12px 14px;
    border-radius:12px;
}}
@media (max-width:980px) {{
    .grid {{
        grid-template-columns:1fr;
    }}
    .row {{
        grid-template-columns:1fr;
    }}
    .title {{
        font-size:24px;
    }}
    .actions {{
        grid-template-columns:1fr;
    }}
}}
</style>
</head>
<body>
<div class="container">
  <a class="back" href="{back_path}">← Назад к списку</a>

  <div class="topline">
    <div>
      <h1 class="title">Карточка заявки</h1>
      <p class="sub">Полная заявка, обсуждение, история и база для аналитики.</p>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-title">Детали заявки</div>
      <div id="taskCard">Загрузка...</div>
    </div>

    <div class="card">
      <div class="card-title">Обсуждение по заявке</div>

      <div class="comment-box">
        <textarea id="commentBody" placeholder="Написать комментарий по заявке..."></textarea>

        <div class="actions">
          <button class="btn" onclick="loadTaskPage()">Обновить</button>
          <button class="btn primary" onclick="sendComment()">Добавить комментарий</button>
        </div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:18px">
    <div class="card-title">Payload</div>
    <div id="payloadBox" class="payload">{{}}</div>
  </div>

  <div class="card" style="margin-top:18px">
    <div class="card-title">Комментарии</div>
    <div id="commentsBox" class="comments">Загрузка...</div>
  </div>
</div>

<script>
const TASK_ID = "{task_id}";

function esc(value) {{
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}}

function fmtDate(value) {{
  if (!value) return "—";
  try {{
    return new Date(value).toLocaleString("ru-RU");
  }} catch {{
    return String(value);
  }}
}}

async function loadTaskPage() {{
  try {{
    const [taskResp, commentsResp] = await Promise.all([
      fetch(`/api/task/${{TASK_ID}}`, {{ credentials: "same-origin" }}),
      fetch(`/api/task/${{TASK_ID}}/comments`, {{ credentials: "same-origin" }})
    ]);

    const taskPayload = await taskResp.json();
    const commentsPayload = await commentsResp.json();

    const taskCard = document.getElementById("taskCard");
    const commentsBox = document.getElementById("commentsBox");
    const payloadBox = document.getElementById("payloadBox");

    if (taskPayload.status !== "ok") {{
      taskCard.innerHTML = `<div class="error">Ошибка загрузки заявки: ${{esc(taskPayload.error || "unknown error")}}</div>`;
      return;
    }}

    const t = taskPayload.data || {{}};

    taskCard.innerHTML = `
      <div class="rows">
        <div class="row"><div class="label">ID</div><div class="value">${{esc(t.id)}}</div></div>
        <div class="row"><div class="label">Portal ID</div><div class="value">${{esc(t.portal_task_id)}}</div></div>
        <div class="row"><div class="label">Магазин</div><div class="value">${{esc(t.store_no)}}${{t.store_name ? ` — ${{esc(t.store_name)}}` : ""}}</div></div>
        <div class="row"><div class="label">Адрес</div><div class="value">${{esc(t.store_address || "—")}}</div></div>
        <div class="row"><div class="label">Статус портала</div><div class="value">${{esc(t.status || "—")}}</div></div>
        <div class="row"><div class="label">Внутренний статус</div><div class="value">${{esc(t.internal_status || "new")}}</div></div>
        <div class="row"><div class="label">SLA</div><div class="value">${{esc(fmtDate(t.sla))}}</div></div>
        <div class="row"><div class="label">Last seen</div><div class="value">${{esc(fmtDate(t.last_seen_at))}}</div></div>
        <div class="row"><div class="label">Менеджер</div><div class="value">${{esc(t.manager_name)}}${{t.manager_email ? ` (${{esc(t.manager_email)}})` : ""}}</div></div>
      </div>
      <div class="meta-badges">
        <span class="badge">Комментариев: ${{esc(t.comments_count ?? 0)}}</span>
        <span class="badge">Роль просмотра: ${{esc(t.viewer_role || "—")}}</span>
      </div>
    `;

    payloadBox.textContent = JSON.stringify(t, null, 2);

    if (commentsPayload.status !== "ok") {{
      commentsBox.innerHTML = `<div class="error">Ошибка загрузки комментариев: ${{esc(commentsPayload.error || "unknown error")}}</div>`;
      return;
    }}

    const rows = commentsPayload.data || [];
    commentsBox.innerHTML = rows.length
      ? rows.map(c => `
          <div class="comment">
            <div class="comment-head">
              <div>
                <strong>${{esc(c.author_name)}}</strong>
                <span class="comment-role">${{esc(c.author_role || "manager")}}</span>
              </div>
              <div>${{esc(fmtDate(c.created_at))}}</div>
            </div>
            <div>${{esc(c.body)}}</div>
          </div>
        `).join("")
      : `<div class="empty">Комментариев пока нет. Здесь будет история общения по заявке.</div>`;

  }} catch (e) {{
    document.getElementById("taskCard").innerHTML = `<div class="error">${{esc(e.message || String(e))}}</div>`;
  }}
}}

async function sendComment() {{
  const textarea = document.getElementById("commentBody");
  const body = (textarea.value || "").trim();
  if (!body) {{
    alert("Введите комментарий");
    return;
  }}

  const resp = await fetch(`/api/task/${{TASK_ID}}/comments`, {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    credentials: "same-origin",
    body: JSON.stringify({{ body }})
  }});

  const payload = await resp.json();
  if (payload.status !== "ok") {{
    alert(payload.error || payload.detail || "Ошибка отправки комментария");
    return;
  }}

  textarea.value = "";
  await loadTaskPage();
}}

window.addEventListener("load", loadTaskPage);
</script>
</body>
</html>
"""


@router.get("/ui/task/{task_id}", response_class=HTMLResponse)
async def ui_task_page(request: Request, task_id: str):
    guard = require_ui_manager_or_dispatcher(request)
    if not isinstance(guard, dict):
        return guard
    back_path = "/ui/tasks" if guard["role"] in {"admin", "dispatcher"} else "/m/tasks"
    return HTMLResponse(render_task_html(task_id, back_path))


# disabled duplicate route: /m/task/{task_id}
# @router.get("/m/task/{task_id}", response_class=HTMLResponse)
async def mobile_task_page(request: Request, task_id: str):
    guard = require_ui_manager_or_dispatcher(request)
    if not isinstance(guard, dict):
        return guard
    back_path = "/ui/tasks" if guard["role"] in {"admin", "dispatcher"} else "/m/tasks"
    return HTMLResponse(render_task_html(task_id, back_path))
