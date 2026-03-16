function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value ?? "—";
}

function formatDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString("ru-RU"); } catch (e) { return String(value); }
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', '&quot;');
}

function getTaskId() {
  const wrap = document.querySelector("[data-task-id]");
  return wrap ? wrap.getAttribute("data-task-id") : null;
}

function renderStatus(value) {
  const badge = document.getElementById("internal_status_badge");
  if (!badge) return;
  const v = value || "new";
  badge.className = `status ${v}`;
  badge.textContent = v;
}

function renderEvents(events) {
  const list = document.getElementById("events");
  list.innerHTML = "";
  if (!events || !events.length) {
    list.innerHTML = '<div class="muted">Нет событий</div>';
    return;
  }

  for (const ev of events) {
    const payload = typeof ev.payload === "string" ? ev.payload : JSON.stringify(ev.payload || {});
    list.insertAdjacentHTML("beforeend", `
      <div class="item">
        <div class="head">
          <strong>${esc(ev.event_type || "—")}</strong>
          <span class="muted">${esc(formatDate(ev.created_at))}</span>
        </div>
        <div class="mono">${esc(payload)}</div>
      </div>
    `);
  }
}

function renderComments(items) {
  const list = document.getElementById("comments");
  list.innerHTML = "";
  if (!items || !items.length) {
    list.innerHTML = '<div class="muted">Нет комментариев</div>';
    return;
  }

  for (const c of items) {
    list.insertAdjacentHTML("beforeend", `
      <div class="item">
        <div class="head">
          <strong>${esc(c.author_name || "—")}</strong>
          <span class="muted">${esc(formatDate(c.created_at))}</span>
        </div>
        <div>${esc(c.comment_text || "")}</div>
      </div>
    `);
  }
}

async function reloadTask() {
  const taskId = getTaskId();
  if (!taskId) return;

  const resp = await fetch(`/api/tasks/${taskId}`, { cache: "no-store" });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Ошибка загрузки карточки");
    return;
  }

  const d = payload.data || {};
  setText("portal_task_id", d.portal_task_id);
  setText("portal_status", d.portal_status);
  renderStatus(d.internal_status);
  setText("store_no", d.store_no);
  setText("manager_name", d.manager_name);
  setText("sla", formatDate(d.sla));
  setText("created_at", formatDate(d.created_at));
  setText("last_seen_at", formatDate(d.last_seen_at));
  setText("accepted_at", `Принято: ${formatDate(d.accepted_at)}`);
  setText("closed_at", `Завершено: ${formatDate(d.closed_at)}`);
  setText("manager_comment", d.manager_comment || "—");
  renderEvents(d.events || []);
  renderComments(d.comments || []);
}

async function acceptTask() {
  const taskId = getTaskId();
  if (!taskId) return;

  const resp = await fetch(`/api/tasks/${taskId}/accept`, { method: "POST" });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Не удалось принять задачу");
    return;
  }
  await reloadTask();
}

async function closeTask() {
  const taskId = getTaskId();
  if (!taskId) return;
  const comment = (document.getElementById("comment_text").value || "").trim();

  const resp = await fetch(`/api/tasks/${taskId}/close`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment: comment || null })
  });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Не удалось завершить задачу");
    return;
  }
  await reloadTask();
}

async function sendComment() {
  const taskId = getTaskId();
  if (!taskId) return;
  const textarea = document.getElementById("comment_text");
  const comment = (textarea.value || "").trim();
  if (!comment) {
    alert("Комментарий пустой");
    return;
  }

  const resp = await fetch(`/api/tasks/${taskId}/comment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment })
  });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Не удалось сохранить комментарий");
    return;
  }

  textarea.value = "";
  await reloadTask();
}

window.addEventListener("load", reloadTask);
