let managersCache = [];
let storesCache = [];

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

function generatePassword(length = 12) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*";
  let out = "";
  for (let i = 0; i < length; i++) {
    out += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return out;
}

function fillGeneratedPassword(id) {
  const input = document.getElementById(`password_${id}`);
  if (!input) return;
  input.value = generatePassword(12);
  input.type = "text";
  const btn = document.getElementById(`toggle_${id}`);
  if (btn) btn.textContent = "Скрыть";
}

function togglePassword(id) {
  const input = document.getElementById(`password_${id}`);
  const btn = document.getElementById(`toggle_${id}`);
  if (!input || !btn) return;

  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "Скрыть";
  } else {
    input.type = "password";
    btn.textContent = "Показать";
  }
}

async function copyPassword(id) {
  const input = document.getElementById(`password_${id}`);
  if (!input) return;
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

async function loadAllData() {
  managersCache = await fetchManagers();
  storesCache = await fetchStores();
  renderManagers();
  renderStores();
}

function renderManagers() {
  const rows = filteredManagers();
  const tbody = document.querySelector("#managersTable tbody");
  tbody.innerHTML = "";
  document.getElementById("managersCount").textContent = `Всего: ${rows.length}`;

  rows.forEach((row) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td><input class="table-input compact-input" id="name_${row.id}" value="${escapeHtml(row.full_name || "")}"></td>
        <td><input class="table-input compact-input" id="email_${row.id}" value="${escapeHtml(row.email || "")}"></td>
        <td>${row.stores_count ?? 0}</td>
        <td>
          <label class="switch">
            <input type="checkbox" id="active_${row.id}" ${row.is_active ? "checked" : ""}>
            <span>${row.is_active ? "Да" : "Нет"}</span>
          </label>
        </td>
        <td>
          <div class="manager-action-card">
            <input class="table-input password-input" id="password_${row.id}" type="password" placeholder="Новый пароль">

            <div class="password-actions-row">
              <button class="mini-btn" type="button" onclick="fillGeneratedPassword('${row.id}')">Сгенерировать</button>
              <button class="mini-btn" type="button" id="toggle_${row.id}" onclick="togglePassword('${row.id}')">Показать</button>
              <button class="mini-btn" type="button" onclick="copyPassword('${row.id}')">Копировать</button>
            </div>

            <div class="manager-main-actions">
              <button class="mini-btn" onclick="updateManager('${row.id}')">Сохранить</button>
              <button class="mini-btn" onclick="changePassword('${row.id}')">Сменить пароль</button>
              <button class="mini-btn danger-btn" onclick="deleteManager('${row.id}')">Удалить</button>
            </div>
          </div>
        </td>
      </tr>
      `
    );
  });

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">Нет менеджеров</td></tr>`;
  }
}

function renderStores() {
  const rows = filteredStores();
  const tbody = document.querySelector("#storesTable tbody");
  tbody.innerHTML = "";
  document.getElementById("storesCount").textContent = `Всего: ${rows.length}`;

  const options = [`<option value="">Не назначен</option>`]
    .concat(managersCache.map(m => `<option value="${m.id}">${escapeHtml(m.full_name || "Без имени")}</option>`))
    .join("");

  rows.forEach((row) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td>
          <div class="store-no">${escapeHtml(row.store_no ?? "—")}</div>
          <div class="store-meta">${escapeHtml(row.name ?? "")}</div>
        </td>
        <td>${escapeHtml(row.manager_name || row.assigned_user_name || "Не назначен")}</td>
        <td>
          <div class="assign-box">
            <select class="table-select" id="assign_${row.id}">
              ${options}
            </select>
            <button class="mini-btn" onclick="assignStore('${row.id}')">Назначить</button>
          </div>
        </td>
      </tr>
      `
    );

    const select = document.getElementById(`assign_${row.id}`);
    if (select) select.value = row.assigned_user_id || "";
  });

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty-cell">Нет магазинов</td></tr>`;
  }
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

async function changePassword(id) {
  const password = document.getElementById(`password_${id}`).value.trim();

  if (!password) {
    alert("Введите новый пароль");
    return;
  }

  const resp = await fetch(`/api/admin/managers/${id}/password`, {
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

  alert("Пароль обновлён");
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.getElementById("createManagerBtn").addEventListener("click", createManager);
document.getElementById("managerSearch").addEventListener("input", renderManagers);
document.getElementById("storeSearch").addEventListener("input", renderStores);

(async function init() {
  await loadAllData();
})();
