(function () {
  const taskId = window.__TASK_ID__;

  const els = {
    id: document.getElementById('task-id'),
    status: document.getElementById('task-status'),
    portalId: document.getElementById('task-portal-id'),
    storeNo: document.getElementById('task-store-no'),
    storeAddress: document.getElementById('task-store-address'),
    sla: document.getElementById('task-sla'),
    lastSeen: document.getElementById('task-last-seen'),
    manager: document.getElementById('task-manager'),
    internalStatus: document.getElementById('task-internal-status'),
    payload: document.getElementById('task-payload'),
    comments: document.getElementById('task-comments'),
    error: document.getElementById('task-error'),
    comment: document.getElementById('task-comment-input'),
    btnReload: document.getElementById('btn-reload-task'),
    btnComment: document.getElementById('btn-add-comment'),
    commentsCountChip: document.getElementById('comments-count-chip'),
    viewerRoleChip: document.getElementById('viewer-role-chip'),
  };

  function managerId() {
    return localStorage.getItem('manager_uuid') || '';
  }

  function reqHeaders(json) {
    const h = {
      'X-User-Id': managerId(),
      'X-User-Role': 'manager',
      'Accept': 'application/json'
    };
    if (json) h['Content-Type'] = 'application/json';
    return h;
  }

  function escapeHtml(v) {
    return String(v || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
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
    try {
      return new Date(v).toLocaleString('ru-RU');
    } catch (_) {
      return String(v);
    }
  }

  async function safeJsonFetch(url, options) {
    const response = await fetch(url, options || {});
    const raw = await response.text();
    const contentType = response.headers.get('content-type') || '';

    let parsed = null;

    if (contentType.includes('application/json')) {
      try {
        parsed = JSON.parse(raw);
      } catch (e) {
        throw new Error(`Сервер вернул повреждённый JSON: ${e.message}`);
      }
    } else {
      const shortBody = raw.slice(0, 300).trim();
      throw new Error(
        `Ожидался JSON, но сервер вернул "${contentType || 'unknown'}": ${shortBody || '[empty body]'}`
      );
    }

    if (!response.ok) {
      const detail =
        (parsed && (parsed.detail || parsed.error || parsed.message)) ||
        `HTTP ${response.status}`;
      throw new Error(detail);
    }

    return parsed;
  }

  function renderComments(items) {
    const list = Array.isArray(items) ? items : [];
    els.commentsCountChip.textContent = `Комментариев: ${list.length}`;

    if (!list.length) {
      els.comments.innerHTML = '<div class="muted">Комментариев пока нет</div>';
      return;
    }

    els.comments.innerHTML = list.map((x) => `
      <div class="comment-card">
        <div class="comment-head">
          <strong>${escapeHtml(x.author_name || '—')}</strong>
          <span>${escapeHtml(fmt(x.created_at))}</span>
        </div>
        <div class="comment-text">${escapeHtml(x.comment_text || x.comment || '')}</div>
      </div>
    `).join('');
  }

  function renderTaskPayload(t) {
    const payload = {
      id: t.id || null,
      portal_task_id: t.portal_task_id || null,
      status: t.status || null,
      internal_status: t.internal_status || null,
      sla: t.sla || t.sla_due_at || null,
      last_seen_at: t.last_seen_at || null,
      store_no: t.store_no || null,
      store_name: t.store_name || null,
      store_address: t.store_address || null,
      manager_name: t.manager_name || null,
      manager_email: t.manager_email || null,
      comments_count: t.comments_count || 0,
      viewer_role: t.viewer_role || 'manager',
      viewer_name: t.viewer_name || null,
    };

    els.payload.textContent = JSON.stringify(payload, null, 2);
  }

  function renderTask(data) {
    const t = data.task || data || {};
    const comments = data.comments || [];

    els.id.textContent = t.id || '—';
    els.status.textContent = t.status || '—';
    els.portalId.textContent = t.portal_task_id || '—';
    els.storeNo.textContent = t.store_no && t.store_name
      ? `${t.store_no} — ${t.store_name}`
      : (t.store_no || t.store_name || '—');

    if (els.storeAddress) {
      els.storeAddress.textContent = t.store_address || '—';
    }

    els.sla.textContent = fmt(t.sla || t.sla_due_at);
    els.lastSeen.textContent = fmt(t.last_seen_at);
    els.manager.textContent = t.manager_name && t.manager_email
      ? `${t.manager_name} (${t.manager_email})`
      : (t.manager_name || t.manager_email || '—');
    els.internalStatus.textContent = t.internal_status || 'new';

    els.viewerRoleChip.textContent = `Роль просмотра: ${t.viewer_role || 'manager'}`;

    renderTaskPayload(t);
    renderComments(comments);
  }

  async function loadTask() {
    clearError();

    if (!managerId()) {
      showError('Сначала сохрани Manager UUID на странице списка заявок');
      return;
    }

    try {
      const taskResponse = await safeJsonFetch(`/api/task/${taskId}`, {
        method: 'GET',
        headers: reqHeaders(false),
        credentials: 'same-origin',
      });

      const commentsResponse = await safeJsonFetch(`/api/task/${taskId}/comments`, {
        method: 'GET',
        headers: reqHeaders(false),
        credentials: 'same-origin',
      });

      const taskData = taskResponse.data || {};
      const commentsData = commentsResponse.data || [];

      renderTask({
        task: taskData,
        comments: commentsData,
      });
    } catch (e) {
      showError(e.message || String(e));
    }
  }

  async function post(url, body) {
    clearError();

    try {
      await safeJsonFetch(url, {
        method: 'POST',
        headers: reqHeaders(true),
        body: JSON.stringify(body || {}),
        credentials: 'same-origin',
      });
      return true;
    } catch (e) {
      showError(e.message || String(e));
      return false;
    }
  }

  if (els.btnReload) {
    els.btnReload.addEventListener('click', function () {
      loadTask();
    });
  }

  if (els.btnComment) {
    els.btnComment.addEventListener('click', async function () {
      const comment = (els.comment.value || '').trim();
      if (!comment) {
        showError('Введите комментарий');
        return;
      }

      const ok = await post(`/api/task/${taskId}/comments`, { comment });
      if (ok) {
        els.comment.value = '';
        await loadTask();
      }
    });
  }

  loadTask();
})();
