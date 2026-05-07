/**
 * CRD — Copilot Roadmap Diff namespace
 * Handles roadmap refresh, diff modal rendering, and change application.
 */
const CRD = (() => {
  let _diffData = null;
  let _syncLogId = null;
  const _modal = () => bootstrap.Modal.getOrCreateInstance(document.getElementById('diffModal'));

  // ── Refresh ─────────────────────────────────────────────────────────────────

  function triggerRefresh() {
    _setOverlay(true);
    fetch('/sync/refresh', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        _setOverlay(false);
        if (data.status === 'no_changes') {
          _toast('success', `<i class="bi bi-check-circle-fill me-1"></i>${data.message}`);
        } else if (data.status === 'changes_detected') {
          _diffData = data.diff;
          _syncLogId = data.sync_log_id;
          _renderDiff(data.diff);
          _modal().show();
        } else {
          _toast('danger', `<i class="bi bi-exclamation-triangle-fill me-1"></i>Error: ${data.message}`);
        }
      })
      .catch(err => {
        _setOverlay(false);
        _toast('danger', `<i class="bi bi-wifi-off me-1"></i>Network error: ${err.message}`);
      });
  }

  // ── Render diff modal ────────────────────────────────────────────────────────

  function _renderDiff(diff) {
    const added = diff.added || [];
    const modified = diff.modified || [];
    const removed = diff.removed || [];
    const unchanged = diff.unchanged || [];

    // Summary badges
    document.getElementById('summaryAdded').textContent = `${added.length} New`;
    document.getElementById('summaryModified').textContent = `${modified.length} Modified`;
    document.getElementById('summaryRemoved').textContent = `${removed.length} Removed`;
    document.getElementById('summaryUnchanged').textContent = `${unchanged.length} Unchanged`;
    document.getElementById('badgeAdded').textContent = added.length;
    document.getElementById('badgeModified').textContent = modified.length;
    document.getElementById('badgeRemoved').textContent = removed.length;
    document.getElementById('badgeUnchanged').textContent = unchanged.length;

    if (diff.detected_at) {
      document.getElementById('diffDetectedAt').textContent =
        `Detected at: ${new Date(diff.detected_at).toLocaleString()}`;
    }

    // Render each pane
    document.getElementById('addedList').innerHTML = _renderAdded(added);
    document.getElementById('modifiedList').innerHTML = _renderModified(modified);
    document.getElementById('removedList').innerHTML = _renderRemoved(removed);
    document.getElementById('unchangedList').innerHTML = _renderUnchanged(unchanged);

    // Auto-switch to first non-empty tab
    if (added.length > 0) _activateTab('tab-added');
    else if (modified.length > 0) _activateTab('tab-modified');
    else if (removed.length > 0) _activateTab('tab-removed');
  }

  function _renderAdded(items) {
    if (!items.length) return '<p class="text-muted py-3 text-center">No new features detected.</p>';
    return `
      <table class="table table-sm diff-table">
        <thead><tr>
          <th width="32"><input type="checkbox" onchange="CRD.selectAll('added', this.checked)"></th>
          <th>Feature Name</th><th>Workload</th><th>Status</th><th>Phase</th><th>GA Estimate</th><th>Readiness</th>
        </tr></thead>
        <tbody>
          ${items.map(f => `
            <tr class="diff-row-added">
              <td><input type="checkbox" class="diff-check-added" value="${_esc(f.feature_id)}" checked></td>
              <td class="fw-medium">${_esc(f.name)}</td>
              <td>${_workloadTag(f.workload)}</td>
              <td>${_statusBadge(f.release_status)}</td>
              <td>${_phaseBadge(f.release_phase)}</td>
              <td>${_esc(f.ga_estimate || '—')}</td>
              <td>${_readinessBadge(f.business_readiness)}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  function _renderModified(items) {
    if (!items.length) return '<p class="text-muted py-3 text-center">No modified features detected.</p>';
    return items.map(item => `
      <div class="diff-modified-card mb-3">
        <div class="diff-modified-header d-flex align-items-center gap-2">
          <input type="checkbox" class="diff-check-modified" value="${_esc(item.feature_id)}" checked
                 data-feature-id="${_esc(item.feature_id)}">
          <strong>${_esc(item.feature_name)}</strong>
          <span class="text-muted small">${_workloadTag(item.workload)}</span>
          <span class="badge bg-warning text-dark ms-auto">${item.changes.length} field${item.changes.length !== 1 ? 's' : ''} changed</span>
        </div>
        <div class="diff-fields-table">
          <table class="table table-sm mb-0">
            <thead><tr>
              <th width="32"></th><th width="180">Field</th><th>Current Value</th><th>New Value</th>
            </tr></thead>
            <tbody>
              ${item.changes.map(ch => `
                <tr>
                  <td><input type="checkbox" class="diff-field-check"
                        data-feature-id="${_esc(item.feature_id)}" data-field="${_esc(ch.field)}" checked></td>
                  <td class="fw-medium small">${_esc(ch.label)}</td>
                  <td class="diff-old-value">${_esc(ch.old_value || '—')}</td>
                  <td class="diff-new-value">${_esc(ch.new_value || '—')}</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>`).join('');
  }

  function _renderRemoved(items) {
    if (!items.length) return '<p class="text-muted py-3 text-center">No features removed from roadmap.</p>';
    return `
      <table class="table table-sm diff-table">
        <thead><tr>
          <th width="32"><input type="checkbox" onchange="CRD.selectAll('removed', this.checked)"></th>
          <th>Feature Name</th><th>Workload</th><th>Last Status</th>
        </tr></thead>
        <tbody>
          ${items.map(f => `
            <tr class="diff-row-removed">
              <td><input type="checkbox" class="diff-check-removed" value="${_esc(f.feature_id)}" checked></td>
              <td class="fw-medium">${_esc(f.feature_name)}</td>
              <td>${_workloadTag(f.workload)}</td>
              <td>${_statusBadge(f.release_status)}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  function _renderUnchanged(items) {
    if (!items.length) return '<p class="text-muted py-3 text-center">No existing features to compare.</p>';
    return `
      <table class="table table-sm diff-table">
        <thead><tr>
          <th>Feature Name</th><th>Workload</th><th>Status</th><th>Phase</th><th>GA Estimate</th><th>Readiness</th>
        </tr></thead>
        <tbody>
          ${items.map(f => `
            <tr class="diff-row-unchanged text-muted">
              <td>${_esc(f.feature_name)}</td>
              <td>${_workloadTag(f.workload)}</td>
              <td>${_statusBadge(f.release_status)}</td>
              <td>${_phaseBadge(f.release_phase)}</td>
              <td>${_esc(f.ga_estimate || '—')}</td>
              <td>${_readinessBadge(f.business_readiness)}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  // ── Apply changes ────────────────────────────────────────────────────────────

  function applyChanges() {
    const btn = document.getElementById('applyChangesBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Applying…';

    // Collect added
    const addedIds = [...document.querySelectorAll('.diff-check-added:checked')]
      .map(el => el.value);

    // Collect modified — per-feature, per-field granularity
    const modifiedMap = {};
    document.querySelectorAll('.diff-field-check:checked').forEach(el => {
      const fid = el.dataset.featureId;
      const field = el.dataset.field;
      if (!modifiedMap[fid]) modifiedMap[fid] = [];
      modifiedMap[fid].push(field);
    });
    const modified = Object.entries(modifiedMap).map(([fid, fields]) => ({
      feature_id: fid, fields,
    }));

    // Collect removed
    const removedIds = [...document.querySelectorAll('.diff-check-removed:checked')]
      .map(el => el.value);

    fetch('/sync/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sync_log_id: _syncLogId,
        added: addedIds,
        modified: modified,
        removed: removedIds,
      }),
    })
      .then(r => r.json())
      .then(data => {
        _modal().hide();
        if (data.status === 'success') {
          _toast('success', `<i class="bi bi-check-circle-fill me-1"></i>${data.applied} change(s) applied. Refreshing page…`);
          setTimeout(() => location.reload(), 1400);
        } else {
          _toast('danger', `Error: ${data.message}`);
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Apply Selected Changes';
        }
      })
      .catch(err => {
        _toast('danger', `Network error: ${err.message}`);
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Apply Selected Changes';
      });
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function selectAll(type, checked) {
    document.querySelectorAll(`.diff-check-${type}`).forEach(el => el.checked = checked);
    // If modifying the modified checkboxes via header, also toggle field-level
    if (type === 'modified') {
      document.querySelectorAll('.diff-field-check').forEach(el => el.checked = checked);
    }
  }

  function _setOverlay(show) {
    const el = document.getElementById('refreshOverlay');
    if (!el) return;
    if (show) {
      el.classList.remove('d-none');
      el.classList.add('d-flex');
    } else {
      el.classList.add('d-none');
      el.classList.remove('d-flex');
    }
  }

  function _activateTab(id) {
    const el = document.getElementById(id);
    if (el) el.click();
  }

  function _toast(type, html) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const id = `toast-${Date.now()}`;
    const bgMap = { success: 'bg-success', danger: 'bg-danger', warning: 'bg-warning text-dark', info: 'bg-info' };
    const bg = bgMap[type] || 'bg-secondary';
    container.insertAdjacentHTML('beforeend', `
      <div id="${id}" class="toast align-items-center text-white ${bg} border-0" role="alert" aria-live="assertive">
        <div class="d-flex">
          <div class="toast-body">${html}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>`);
    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  }

  function _esc(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _statusBadge(s) {
    const cls = (s || '').toLowerCase().replace(/ /g, '-');
    return `<span class="status-badge status-${cls}">${_esc(s || '—')}</span>`;
  }

  function _phaseBadge(p) {
    const cls = (p || '').toLowerCase().replace(/ /g, '-');
    return `<span class="phase-badge phase-${cls}">${_esc(p || '—')}</span>`;
  }

  function _readinessBadge(r) {
    const icon = r === 'Safe to Promote' ? '✅' : r === 'Pilot Only' ? '⚠️' : r === 'Do Not Commit' ? '❌' : '';
    const cls = (r || '').toLowerCase().replace(/ /g, '-');
    return `<span class="readiness-badge readiness-${cls}">${icon} ${_esc(r || '—')}</span>`;
  }

  function _workloadTag(w) {
    return `<span class="workload-tag">${_esc(w || '—')}</span>`;
  }

  // Public API
  return { triggerRefresh, applyChanges, selectAll };
})();
