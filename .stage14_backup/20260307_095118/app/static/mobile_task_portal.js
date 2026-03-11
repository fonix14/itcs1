function actorHeaders() {
  const userId = localStorage.getItem("itcs_user_id") || "";
  const userRole = localStorage.getItem("itcs_user_role") || "";
  const headers = {};
  if (userId) headers["X-User-Id"] = userId;
  if (userRole) headers["X-User-Role"] = userRole;
  return headers;
}

async function ensureActor() {
  let userId = localStorage.getItem("itcs_user_id");
  let userRole = localStorage.getItem("itcs_user_role");

  if (!userId) {
    userId = prompt("Введите UUID пользователя (X-User-Id):", localStorage.getItem("itcs_user_id") || "") || "";
    if (userId) localStorage.setItem("itcs_user_id", userId);
  }

  if (!userRole) {
    userRole = prompt("Введите роль (manager / dispatcher):", localStorage.getItem("itcs_user_role") || "manager") || "";
    if (userRole) localStorage.setItem("itcs_user_role", userRole.toLowerCase());
  }

  const resp = await fetch("/api/mobile/me", { headers: actorHeaders() });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    throw new Error(payload.detail || payload.error || "Не удалось определить пользователя");
  }
  const d = payload.data || {};
  document.getElementById("profile").textContent = `Пользователь: ${d.display_name} • Роль: ${d.role}`;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "—";
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
    list.innerHTML = "<li>Нет событий</li>";
    return;
  }
  for (const ev of events) {
    const li = document.createElement("li");
    const payload = typeof ev.payload === "string" ? ev.payload : JSON.stringify(ev.payload);
    li.textContent = `${ev.created_at ?? "—"} | ${ev.event_type ?? "—"} | ${payload}`;
    list.appendChild(li);
  }
}

function renderAttachments(items) {
  const box = document.getElementById("attachments");
  box.innerHTML = "";
  if (!items || !items.length) {
    box.textContent = "Нет фото";
    return;
  }

  for (const item of items) {
    const div = document.createElement("div");
    div.className = "att";

    const title = document.createElement("div");
    title.className = "att-title";
    title.textContent = `${item.file_name ?? "photo"} • ${formatDate(item.created_at)}`;
    div.appendChild(title);

    if (item.preview_url) {
      const img = document.createElement("img");
      img.src = item.preview_url;
      img.alt = item.file_name || "photo";
      div.appendChild(img);
    }

    box.appendChild(div);
  }
}

async function reloadTask() {
  const taskId = getTaskId();
  if (!taskId) return;

  await ensureActor();

  const resp = await fetch(`/api/mobile/tasks/${taskId}`, { headers: actorHeaders() });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.detail || payload.error || "Ошибка загрузки карточки");
    return;
  }

  const d = payload.data || {};
  setText("portal_task_id", d.portal_task_id);
  setText("status", d.status);
  setText("store_no", d.store_no);
  setText("manager_name", d.manager_name);
  setText("sla", formatDate(d.sla));
  renderEvents(d.events || []);
  renderAttachments(d.attachments || []);
}

async function acceptTask() {
  const taskId = getTaskId();
  const resp = await fetch(`/api/mobile/tasks/${taskId}/accept`, {
    method: "POST",
    headers: actorHeaders(),
  });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.detail || payload.error || "Не удалось принять задачу");
    return;
  }
  await reloadTask();
}

async function sendComment() {
  const taskId = getTaskId();
  const textarea = document.getElementById("comment_text");
  const comment = (textarea.value || "").trim();
  if (!comment) {
    alert("Комментарий пустой");
    return;
  }

  const resp = await fetch(`/api/mobile/tasks/${taskId}/comment`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...actorHeaders() },
    body: JSON.stringify({ comment })
  });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.detail || payload.error || "Не удалось сохранить комментарий");
    return;
  }

  textarea.value = "";
  await reloadTask();
}

async function uploadPhoto() {
  const taskId = getTaskId();
  const input = document.getElementById("photo_input");
  const file = input.files && input.files[0];
  if (!file) {
    alert("Выбери фото");
    return;
  }

  const form = new FormData();
  form.append("file", file);

  const resp = await fetch(`/api/tasks/${taskId}/attachments`, {
    method: "POST",
    headers: actorHeaders(),
    body: form
  });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.detail || payload.error || "Не удалось загрузить фото");
    return;
  }

  input.value = "";
  await reloadTask();
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(console.error);
  });
}

window.addEventListener("load", reloadTask);
