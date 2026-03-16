let managersCache = [];
let storesCache = [];
let currentPasswordManagerId = null;
let currentPasswordManagerTitle = "";

async function fetchManagers() {
  const resp = await fetch("/api/admin/managers", { credentials: "same-origin" });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка загрузки менеджеров");
    return [];
  }
  return payload.data || [];
}

async function fetchStores() {
  const resp = await fetch("/api/admin/stores", { credentials: "same-origin" });
  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка загрузки магазинов");
    return [];
  }
  return payload.data || [];
}

function managerFilterValue() {
  return (document.getElementById("managerSearch")?.value || "").trim().toLowerCase();
}

function storeFilterValue() {
  return (document.getElementById("storeSearch")?.value || "").trim().toLowerCase();
}

function filteredManagers() {
  const q = managerFilterValue();
  if (!q) return managersCache;
  return managersCache.filter(row =>
    String(row.full_name || "").toLowerCase().includes(q) ||
    String(row.email || "").toLowerCase().includes(q)
  );
}

function filteredStores() {
  const q = storeFilterValue();
  if (!q) return storesCache;
  return storesCache.filter(row =>
    String(row.store_no || "").toLowerCase().includes(q) ||
    String(row.name || "").toLowerCase().includes(q) ||
    String(row.address || "").toLowerCase().includes(q) ||
    String(row.manager_name || row.assigned_user_name || "").toLowerCase().includes(q)
  );
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function generatePassword(length = 12) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*";
  let out = "";
  for (let i = 0; i < length; i++) {
    out += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return out;
}

async function loadAllData() {
  managersCache = await fetchManagers();
  storesCache = await fetchStores();
  renderManagers();
  renderStores();
}

function renderManagers() {
  const rows = filteredManagers();
  const wrap = document.getElementById("managersCards");
  document.getElementById("managersCount").textContent = `Всего: ${rows.length}`;

  if (!rows.length) {
    wrap.innerHTML = `<div class="empty-card">Нет менеджеров</div>`;
    return;
  }

  wrap.innerHTML = rows.map((row) => `
    <div class="manager-card">
      <div class="manager-card-head">
        <div class="manager-title">${escapeHtml(row.full_name || "Без имени")}</div>
        <div class="manager-badge">${row.is_active ? "Активен" : "Отключен"}</div>
      </div>

      <div class="manager-meta">
        <div class="field">
          <label>ФИО</label>
          <input class="table-input" id="name_${row.id}" value="${escapeHtml(row.full_name || "")}">
        </div>

        <div class="field">
          <label>Email</label>
          <input class="table-input" id="email_${row.id}" value="${escapeHtml(row.email || "")}">
        </div>
      </div>

      <div class="manager-stats">
        <div class="stat-box">
          <div class="stat-label">Магазинов</div>
          <div class="stat-value">${row.stores_count ?? 0}</div>
        </div>

        <div class="stat-box">
          <div class="stat-label">Активность</div>
          <div class="stat-value">
            <label class="switch">
              <input type="checkbox" id="active_${row.id}" ${row.is_active ? "checked" : ""}>
              <span>${row.is_active ? "Да" : "Нет"}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="manager-actions">
        <button class="mini-btn" onclick="updateManager('${row.id}')">Сохранить</button>
        <button class="mini-btn" onclick="openPasswordModal('${row.id}', '${escapeHtml(row.full_name || "Менеджер")}')">Пароль</button>
        <button class="mini-btn danger-btn" onclick="deleteManager('${row.id}')">Удалить</button>
      </div>
    </div>
  `).join("");
}

function renderStores() {
  const rows = filteredStores();
  const wrap = document.getElementById("storesList");
  document.getElementById("storesCount").textContent = `Всего: ${rows.length}`;

  if (!rows.length) {
    wrap.innerHTML = `<div class="empty-card">Нет магазинов</div>`;
    return;
  }

  const options = [`<option value="">Не назначен</option>`]
    .concat(managersCache.map(m => `<option value="${m.id}">${escapeHtml(m.full_name || "Без имени")}</option>`))
    .join("");

  wrap.innerHTML = rows.map((row) => `
    <div class="store-card">
      <div class="store-card-head">
        <div>
          <div class="store-no">${escapeHtml(row.store_no ?? "—")}</div>
          <div class="store-meta">${escapeHtml(row.name ?? "")}</div>
        </div>
        <div class="store-manager">${escapeHtml(row.manager_name || row.assigned_user_name || "Не назначен")}</div>
      </div>

      <div class="assign-box">
        <select class="table-select" id="assign_${row.id}">
          ${options}
        </select>
        <button class="mini-btn" onclick="assignStore('${row.id}')">Назначить</button>
      </div>
    </div>
  `).join("");

  rows.forEach((row) => {
    const select = document.getElementById(`assign_${row.id}`);
    if (select) select.value = row.assigned_user_id || "";
  });
}

async function createManager() {
  const full_name = document.getElementById("managerName").value.trim();
  const email = document.getElementById("managerEmail").value.trim();

  if (!full_name) {
    alert("Укажи ФИО менеджера");
    return;
  }

  const resp = await fetch("/api/admin/managers", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({ full_name, email: email || null })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Ошибка создания менеджера");
    return;
  }

  document.getElementById("managerName").value = "";
  document.getElementById("managerEmail").value = "";

  await loadAllData();
}

async function updateManager(id) {
  const full_name = document.getElementById(`name_${id}`).value.trim();
  const email = document.getElementById(`email_${id}`).value.trim();
  const is_active = document.getElementById(`active_${id}`).checked;

  const resp = await fetch(`/api/admin/managers/${id}`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({ full_name, email: email || null, is_active })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Ошибка обновления менеджера");
    return;
  }

  await loadAllData();
}

function openPasswordModal(id, title) {
  currentPasswordManagerId = id;
  currentPasswordManagerTitle = title;
  document.getElementById("passwordModalSub").textContent = title;
  document.getElementById("modalPasswordInput").value = "";
  document.getElementById("modalPasswordInput").type = "password";
  document.getElementById("modalToggleBtn").textContent = "Показать";
  document.getElementById("passwordModal").classList.remove("hidden");
}

function closePasswordModal() {
  currentPasswordManagerId = null;
  currentPasswordManagerTitle = "";
  document.getElementById("passwordModal").classList.add("hidden");
}

function modalGeneratePassword() {
  const input = document.getElementById("modalPasswordInput");
  input.value = generatePassword(12);
  input.type = "text";
  document.getElementById("modalToggleBtn").textContent = "Скрыть";
}

function modalTogglePassword() {
  const input = document.getElementById("modalPasswordInput");
  const btn = document.getElementById("modalToggleBtn");
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "Скрыть";
  } else {
    input.type = "password";
    btn.textContent = "Показать";
  }
}

async function modalCopyPassword() {
  const input = document.getElementById("modalPasswordInput");
  const value = input.value.trim();
  if (!value) {
    alert("Пароль пуст");
    return;
  }
  try {
    await navigator.clipboard.writeText(value);
    alert("Пароль скопирован");
  } catch {
    input.select();
    document.execCommand("copy");
    alert("Пароль скопирован");
  }
}

async function modalSavePassword() {
  if (!currentPasswordManagerId) return;

  const password = document.getElementById("modalPasswordInput").value.trim();
  if (!password) {
    alert("Введите новый пароль");
    return;
  }

  const resp = await fetch(`/api/admin/managers/${currentPasswordManagerId}/password`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({ password })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Ошибка смены пароля");
    return;
  }

  alert(`Пароль обновлён для: ${currentPasswordManagerTitle}`);
  closePasswordModal();
}

async function deleteManager(id) {
  if (!confirm("Удалить менеджера? Его магазины будут сняты с назначения.")) return;

  const resp = await fetch(`/api/admin/managers/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  const payload = await resp.json();

  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Ошибка удаления менеджера");
    return;
  }

  await loadAllData();
}

async function assignStore(storeId) {
  const assigned_user_id = document.getElementById(`assign_${storeId}`).value || null;

  const resp = await fetch(`/api/admin/stores/${storeId}/assign`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({ assigned_user_id })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || payload.detail || "Ошибка назначения магазина");
    return;
  }

  await loadAllData();
}

document.getElementById("createManagerBtn").addEventListener("click", createManager);
document.getElementById("managerSearch").addEventListener("input", renderManagers);
document.getElementById("storeSearch").addEventListener("input", renderStores);

(async function init() {
  await loadAllData();
})();
