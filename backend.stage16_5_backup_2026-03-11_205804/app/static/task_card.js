function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value ?? "—";
}

function formatDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString(); } catch (e) { return String(value); }
}

function getTaskId() {
  const wrap = document.querySelector("[data-task-id]");
  return wrap ? wrap.getAttribute("data-task-id") : null;
}

function renderEvents(events) {
  const list = document.getElementById("events");
  list.innerHTML = "";
  if (!events || !events.length) {
    list.innerHTML = '<li class="muted">Нет событий</li>';
    return;
  }

  for (const ev of events) {
    const li = document.createElement("li");
    const payload = typeof ev.payload === "string" ? ev.payload : JSON.stringify(ev.payload);
    li.textContent = `${ev.created_at ?? "—"} | ${ev.event_type ?? "—"} | ${payload}`;
    list.appendChild(li);
  }
}

async function reloadTask() {
  const taskId = getTaskId();
  if (!taskId) return;

  const resp = await fetch(`/api/tasks/${taskId}`);
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert("Ошибка загрузки карточки");
    return;
  }

  const d = payload.data || {};
  setText("portal_task_id", d.portal_task_id);
  setText("status", d.status);
  setText("store_no", d.store_no);
  setText("manager_name", d.manager_name);
  setText("sla", formatDate(d.sla));
  setText("last_seen_at", formatDate(d.last_seen_at));
  renderEvents(d.events || []);
}

async function acceptTask() {
  const taskId = getTaskId();
  if (!taskId) return;

  const resp = await fetch(`/api/tasks/${taskId}/accept`, { method: "POST" });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert("Не удалось принять задачу");
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
    alert("Не удалось сохранить комментарий");
    return;
  }

  textarea.value = "";
  await reloadTask();
}

window.addEventListener("load", reloadTask);
