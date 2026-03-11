let managersCache = [];

async function fetchManagers() {
  const resp = await fetch("/api/admin/managers");
  const payload = await resp.json();
  if (payload.status !== "ok") return [];
  return payload.data || [];
}

async function fetchStores() {
  const resp = await fetch("/api/admin/stores");
  const payload = await resp.json();
  if (payload.status !== "ok") return [];
  return payload.data || [];
}

async function renderManagers() {
  managersCache = await fetchManagers();
  const tbody = document.querySelector("#managersTable tbody");
  tbody.innerHTML = "";

  managersCache.forEach((row) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td><input class="table-input" id="name_${row.id}" value="${row.full_name || ""}"></td>
        <td><input class="table-input" id="email_${row.id}" value="${row.email || ""}"></td>
        <td>${row.stores_count ?? 0}</td>
        <td>
          <button class="mini-btn" onclick="updateManager('${row.id}')">Сохранить</button>
          <button class="mini-btn danger-btn" onclick="deleteManager('${row.id}')">Удалить</button>
        </td>
      </tr>
      `
    );
  });
}

async function renderStores() {
  const stores = await fetchStores();
  const tbody = document.querySelector("#storesTable tbody");
  tbody.innerHTML = "";

  const options = [`<option value="">Не назначен</option>`]
    .concat(managersCache.map(m => `<option value="${m.id}">${m.full_name}</option>`))
    .join("");

  stores.forEach((row) => {
    tbody.insertAdjacentHTML(
      "beforeend",
      `
      <tr>
        <td>${row.store_no ?? "—"}</td>
        <td>${row.manager_name ?? "Не назначен"}</td>
        <td>
          <select class="table-select" id="assign_${row.id}">
            ${options}
          </select>
          <button class="mini-btn" onclick="assignStore('${row.id}')">Назначить</button>
        </td>
      </tr>
      `
    );

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
    body: JSON.stringify({ full_name, email: email || null })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка создания менеджера");
    return;
  }

  document.getElementById("managerName").value = "";
  document.getElementById("managerEmail").value = "";

  await renderManagers();
  await renderStores();
}

async function updateManager(id) {
  const full_name = document.getElementById(`name_${id}`).value.trim();
  const email = document.getElementById(`email_${id}`).value.trim();

  const resp = await fetch(`/api/admin/managers/${id}`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ full_name, email: email || null })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка обновления менеджера");
    return;
  }

  await renderManagers();
  await renderStores();
}

async function deleteManager(id) {
  if (!confirm("Удалить менеджера и снять назначение с его магазинов?")) return;

  const resp = await fetch(`/api/admin/managers/${id}`, { method: "DELETE" });
  const payload = await resp.json();

  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка удаления менеджера");
    return;
  }

  await renderManagers();
  await renderStores();
}

async function assignStore(storeId) {
  const assigned_user_id = document.getElementById(`assign_${storeId}`).value || null;

  const resp = await fetch(`/api/admin/stores/${storeId}/assign`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ assigned_user_id })
  });

  const payload = await resp.json();
  if (payload.status !== "ok") {
    alert(payload.error || "Ошибка назначения магазина");
    return;
  }

  await renderManagers();
  await renderStores();
}

document.getElementById("createManagerBtn").addEventListener("click", createManager);

(async function init() {
  await renderManagers();
  await renderStores();
})();
