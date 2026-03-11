(function () {
  const taskId = window.__TASK_ID__;
  const els = {
    status: document.getElementById('task-status'),
    portalId: document.getElementById('task-portal-id'),
    storeNo: document.getElementById('task-store-no'),
    sla: document.getElementById('task-sla'),
    lastSeen: document.getElementById('task-last-seen'),
    manager: document.getElementById('task-manager'),
    internalStatus: document.getElementById('task-internal-status'),
    payload: document.getElementById('task-payload'),
    comments: document.getElementById('task-comments'),
    error: document.getElementById('task-error'),
    comment: document.getElementById('task-comment-input'),
    btnReload: document.getElementById('btn-reload-task'),
    btnAccept: document.getElementById('btn-accept-task'),
    btnComment: document.getElementById('btn-add-comment'),
    btnClose: document.getElementById('btn-close-task'),
  };

  function managerId() { return localStorage.getItem('manager_uuid') || ''; }

  function reqHeaders(json) {
    const h = { 'X-User-Id': managerId(), 'X-User-Role': 'manager' };
    if (json) h['Content-Type'] = 'application/json';
    return h;
  }

  function showError(msg) {
    els.error.textContent = msg || 'Ошибка';
    els.error.style.display = 'block';
  }

  function clearError() {
    els.error.textContent = '';
    els.error.style.display = 'none';
  }

  function fmt(v) {
    if (!v) return '—';
    try { return new Date(v).toLocaleString(); } catch (_) { return String(v); }
  }

  function renderComments(items) {
    if (!items || !items.length) {
      els.comments.innerHTML = '<div class="muted">Комментариев пока нет</div>';
      return;
    }
    els.comments.innerHTML = items.map((x) => `
      <div class="comment-card">
        <div class="comment-head">
          <strong>${x.author_name || '—'}</strong>
          <span>${fmt(x.created_at)}</span>
        </div>
        <div class="comment-text">${(x.comment_text || '').replace(/</g, '&lt;')}</div>
      </div>
    `).join('');
  }

  function renderTask(data) {
    const t = data.task || {};
    els.status.textContent = t.status || '—';
    els.portalId.textContent = t.portal_task_id || '—';
    els.storeNo.textContent = t.store_no || '—';
    els.sla.textContent = fmt(t.sla);
    els.lastSeen.textContent = fmt(t.last_seen_at);
    els.manager.textContent = t.manager_name || '—';
    els.internalStatus.textContent = t.internal_status || 'new';
    els.payload.textContent = JSON.stringify(t.payload || {}, null, 2);
    renderComments(data.comments || []);
  }

  async function loadTask() {
    clearError();

    if (!managerId()) {
      showError('Сначала сохрани Manager UUID на странице списка заявок');
      return;
    }

    const r = await fetch(`/api/mobile/task/${taskId}`, { headers: reqHeaders(false) });
    const data = await r.json();

    if (!r.ok || data.status !== 'ok') {
      showError((data && (data.detail || data.error)) || 'Не удалось загрузить карточку');
      return;
    }

    renderTask(data.data);
  }

  async function post(url, body) {
    clearError();

    const r = await fetch(url, {
      method: 'POST',
      headers: reqHeaders(true),
      body: JSON.stringify(body || {}),
    });

    const data = await r.json();

    if (!r.ok || data.status !== 'ok') {
      showError((data && (data.detail || data.error)) || 'Ошибка операции');
      return false;
    }

    return true;
  }

  els.btnReload.addEventListener('click', () => { loadTask(); });

  els.btnAccept.addEventListener('click', async () => {
    if (await post(`/api/mobile/task/${taskId}/accept`, {})) loadTask();
  });

  els.btnComment.addEventListener('click', async () => {
    const comment = (els.comment.value || '').trim();
    if (!comment) return showError('Введите комментарий');

    if (await post(`/api/mobile/task/${taskId}/comment`, { comment })) {
      els.comment.value = '';
      loadTask();
    }
  });

  els.btnClose.addEventListener('click', async () => {
    const comment = (els.comment.value || '').trim();

    if (await post(`/api/mobile/task/${taskId}/close`, { comment: comment || null })) {
      loadTask();
    }
  });

  loadTask().catch((e) => showError(e.message || String(e)));
})();
