/**
 * FM — Feature Matrix namespace
 * Inline editing, custom columns, notes, add/delete features.
 */
const FM = (() => {
  let _notesFeatureId = null;
  let _table = null;

  // ── Init ────────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    _initTable();
    _initInlineEdit();
    _initCustomCells();
    _initFilters();
    _initSelectAll();
  });

  // ── DataTable ────────────────────────────────────────────────────────────────

  function _initTable() {
    const el = document.getElementById('featureTable');
    if (!el) return;
    _table = $('#featureTable').DataTable({
      pageLength: 50,
      lengthMenu: [25, 50, 100, 200],
      order: [[2, 'asc'], [1, 'asc']],
      columnDefs: [
        { orderable: false, targets: [0, -1] },
      ],
      language: {
        search: '',
        searchPlaceholder: 'Search features…',
        info: 'Showing _START_–_END_ of _TOTAL_ features',
      },
      dom: "<'row align-items-center mb-2'<'col-sm-6'l><'col-sm-6'f>>rt<'row mt-2'<'col-sm-6'i><'col-sm-6'p>>",
      scrollX: true,
    });
  }

  // ── Inline editing ───────────────────────────────────────────────────────────

  function _initInlineEdit() {
    document.querySelectorAll('.editable-cell').forEach(cell => {
      cell.style.cursor = 'pointer';
      cell.title = 'Click to edit';
      cell.addEventListener('click', e => _startEdit(e.currentTarget));
    });
  }

  function _startEdit(cell) {
    if (cell.querySelector('input, select')) return; // already editing

    const featureId = cell.dataset.id;
    const field = cell.dataset.field;
    const type = cell.dataset.type || 'text';
    const currentText = cell.dataset.originalText || cell.textContent.replace(/✅|⚠️|❌/g, '').trim();
    cell.dataset.originalText = currentText;

    let input;
    if (type === 'select') {
      const options = JSON.parse(cell.dataset.options || '[]');
      input = document.createElement('select');
      input.className = 'form-select form-select-sm edit-select';
      options.forEach(opt => {
        const o = document.createElement('option');
        o.value = opt;
        o.textContent = opt;
        if (opt === currentText) o.selected = true;
        input.appendChild(o);
      });
    } else {
      input = document.createElement('input');
      input.type = 'text';
      input.className = 'form-control form-control-sm edit-input';
      input.value = currentText;
    }

    const originalHTML = cell.innerHTML;
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    if (input.tagName === 'INPUT') input.select();

    const save = () => {
      const newVal = input.value;
      if (newVal === currentText) {
        cell.innerHTML = originalHTML;
        _initCellClick(cell);
        return;
      }
      _saveField(featureId, field, newVal, cell, originalHTML);
    };

    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
      if (e.key === 'Escape') { cell.innerHTML = originalHTML; _initCellClick(cell); }
    });
  }

  function _initCellClick(cell) {
    cell.style.cursor = 'pointer';
    cell.addEventListener('click', e => _startEdit(e.currentTarget), { once: true });
  }

  function _saveField(featureId, field, newVal, cell, originalHTML) {
    fetch(`/features/api/update/${featureId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [field]: newVal }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          _updateCellDisplay(cell, field, newVal);
          _initCellClick(cell);
          _showMiniToast(cell, '✓ Saved');
        } else {
          cell.innerHTML = originalHTML;
          _initCellClick(cell);
        }
      })
      .catch(() => { cell.innerHTML = originalHTML; _initCellClick(cell); });
  }

  function _updateCellDisplay(cell, field, value) {
    cell.dataset.originalText = value;
    const statusIcons = { 'Safe to Promote': '✅ ', 'Pilot Only': '⚠️ ', 'Do Not Commit': '❌ ' };
    const prefix = statusIcons[value] || '';
    const slg = value.toLowerCase().replace(/ /g, '-');

    cell.className = cell.className.replace(/status-\S+|phase-\S+|readiness-\S+|confidence-\S+/g, '');

    if (field === 'release_status') {
      cell.classList.add(`status-badge`, `status-${slg}`);
    } else if (field === 'release_phase') {
      cell.classList.add(`phase-badge`, `phase-${slg}`);
    } else if (field === 'business_readiness') {
      cell.classList.add(`readiness-badge`, `readiness-${slg}`);
    } else if (field === 'confidence_level') {
      cell.classList.add(`confidence-dot`, `confidence-${slg}`);
    }

    cell.textContent = prefix + value;
  }

  function _showMiniToast(cell, msg) {
    const t = document.createElement('span');
    t.className = 'save-toast';
    t.textContent = msg;
    cell.appendChild(t);
    setTimeout(() => t.remove(), 1800);
  }

  // ── Custom column cells ──────────────────────────────────────────────────────

  function _initCustomCells() {
    document.querySelectorAll('.editable-custom').forEach(cell => {
      cell.style.cursor = 'pointer';
      cell.title = 'Click to edit';
      cell.addEventListener('click', e => _startCustomEdit(e.currentTarget));
    });
  }

  function _startCustomEdit(cell) {
    if (cell.querySelector('input, select, textarea')) return;

    const featureId = cell.dataset.featureId;
    const colId = cell.dataset.colId;
    const colType = cell.dataset.colType;
    const currentVal = cell.textContent.trim();
    let input;

    if (colType === 'checkbox') {
      input = document.createElement('select');
      input.className = 'form-select form-select-sm';
      ['', 'Yes', 'No'].forEach(opt => {
        const o = document.createElement('option');
        o.value = opt;
        o.textContent = opt || '—';
        if (opt === currentVal) o.selected = true;
        input.appendChild(o);
      });
    } else if (colType === 'dropdown') {
      const opts = JSON.parse(cell.dataset.options || '[]');
      input = document.createElement('select');
      input.className = 'form-select form-select-sm';
      ['', ...opts].forEach(opt => {
        const o = document.createElement('option');
        o.value = opt;
        o.textContent = opt || '—';
        if (opt === currentVal) o.selected = true;
        input.appendChild(o);
      });
    } else if (colType === 'date') {
      input = document.createElement('input');
      input.type = 'date';
      input.className = 'form-control form-control-sm';
      input.value = currentVal;
    } else {
      input = document.createElement('input');
      input.type = 'text';
      input.className = 'form-control form-control-sm';
      input.value = currentVal;
    }

    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();

    const save = () => {
      const newVal = input.value;
      fetch('/features/api/custom-value', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feature_id: parseInt(featureId), column_id: parseInt(colId), value: newVal }),
      })
        .then(() => {
          cell.textContent = newVal;
          cell.style.cursor = 'pointer';
          cell.addEventListener('click', e => _startCustomEdit(e.currentTarget), { once: true });
        });
    };

    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
      if (e.key === 'Escape') { cell.textContent = currentVal; _initCustom(cell); }
    });
  }

  function _initCustom(cell) {
    cell.style.cursor = 'pointer';
    cell.addEventListener('click', e => _startCustomEdit(e.currentTarget), { once: true });
  }

  // ── Multi-select filters (Tom Select) ──────────────────────────────────────

  const FM_FILTERS = [
    { elId: 'fmFilterWorkload',   dataKey: 'workload' },
    { elId: 'fmFilterStatus',     dataKey: 'status' },
    { elId: 'fmFilterPhase',      dataKey: 'phase' },
    { elId: 'fmFilterGaEstimate', dataKey: 'ga' },
    { elId: 'fmFilterReadiness',  dataKey: 'readiness' },
    { elId: 'fmFilterSource',     dataKey: 'source' },
  ];

  const _fmTS = {};

  function _initFilters() {
    FM_FILTERS.forEach(({ elId }) => {
      const el = document.getElementById(elId);
      if (!el) return;
      _fmTS[elId] = new TomSelect(el, {
        plugins: ['remove_button', 'checkbox_options'],
        maxItems: null,
        closeAfterSelect: false,
        hideSelected: false,
        onChange: _applyFilters,
      });
    });
  }

  function _applyFilters() {
    let anyActive = false;

    const selected = {};
    FM_FILTERS.forEach(({ elId, dataKey }) => {
      const ts = _fmTS[elId];
      const vals = ts ? [].concat(ts.getValue()).filter(Boolean) : [];
      selected[dataKey] = vals;
      if (vals.length) anyActive = true;
    });

    const clearBtn = document.getElementById('fmClearFiltersBtn');
    if (clearBtn) clearBtn.style.display = anyActive ? '' : 'none';

    let visible = 0;
    document.querySelectorAll('#featureTableBody tr.feature-row').forEach(row => {
      const ok = FM_FILTERS.every(({ dataKey }) => {
        const vals = selected[dataKey];
        return !vals.length || vals.includes(row.dataset[dataKey] || '');
      });
      row.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });

    const countEl = document.getElementById('fmFilterCount');
    if (countEl) {
      const total = document.querySelectorAll('#featureTableBody tr.feature-row').length;
      countEl.textContent = anyActive ? `Showing ${visible} of ${total} features` : '';
    }

    if (_table) _table.draw(false);
  }

  function clearFilters() {
    Object.values(_fmTS).forEach(ts => ts.clear());
    _applyFilters();
  }

  function exportFiltered() {
    const paramMap = {
      fmFilterWorkload:   'workload',
      fmFilterStatus:     'status',
      fmFilterPhase:      'phase',
      fmFilterGaEstimate: 'ga',
      fmFilterReadiness:  'readiness',
    };
    const params = new URLSearchParams();
    for (const [elId, param] of Object.entries(paramMap)) {
      const ts = _fmTS[elId];
      if (ts) [].concat(ts.getValue()).filter(Boolean).forEach(v => params.append(param, v));
    }
    window.location.href = '/export/excel?' + params.toString();
  }

  // ── Select all rows ──────────────────────────────────────────────────────────

  function _initSelectAll() {
    const master = document.getElementById('selectAllRows');
    if (!master) return;
    master.addEventListener('change', () => {
      document.querySelectorAll('.row-select').forEach(cb => cb.checked = master.checked);
    });
  }

  // ── Add Feature ──────────────────────────────────────────────────────────────

  function openAddFeature() {
    const m = bootstrap.Modal.getOrCreateInstance(document.getElementById('addFeatureModal'));
    m.show();
  }

  function saveNewFeature() {
    const name = document.getElementById('newFeatureName').value.trim();
    if (!name) { document.getElementById('newFeatureName').classList.add('is-invalid'); return; }

    fetch('/features/api/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        workload: document.getElementById('newFeatureWorkload').value.trim(),
        ga_estimate: document.getElementById('newFeatureGA').value.trim(),
        release_status: document.getElementById('newFeatureStatus').value,
        release_phase: document.getElementById('newFeaturePhase').value,
        business_readiness: document.getElementById('newFeatureReadiness').value,
        confidence_level: document.getElementById('newFeatureConfidence').value,
        visible_in_tenant: document.getElementById('newFeatureVisible').value,
        license_required: document.getElementById('newFeatureLicense').value.trim(),
        description: document.getElementById('newFeatureDesc').value.trim(),
      }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          bootstrap.Modal.getInstance(document.getElementById('addFeatureModal')).hide();
          location.reload();
        }
      });
  }

  // ── Delete Feature ───────────────────────────────────────────────────────────

  function deleteFeature(featureId, event) {
    event.stopPropagation();
    if (!confirm('Delete this feature? This cannot be undone.')) return;
    fetch(`/features/api/delete/${featureId}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          const row = document.getElementById(`row-${featureId}`);
          if (row) row.remove();
          if (_table) _table.draw(false);
        }
      });
  }

  // ── Add Column ───────────────────────────────────────────────────────────────

  function openAddColumn() {
    document.getElementById('newColName').value = '';
    document.getElementById('newColType').value = 'text';
    document.getElementById('newColOptions').value = '';
    document.getElementById('dropdownOptionsGroup').classList.add('d-none');
    bootstrap.Modal.getOrCreateInstance(document.getElementById('addColumnModal')).show();
  }

  function toggleColOptions() {
    const type = document.getElementById('newColType').value;
    document.getElementById('dropdownOptionsGroup').classList.toggle('d-none', type !== 'dropdown');
  }

  function saveNewColumn() {
    const name = document.getElementById('newColName').value.trim();
    if (!name) { document.getElementById('newColName').classList.add('is-invalid'); return; }
    const type = document.getElementById('newColType').value;
    const rawOpts = document.getElementById('newColOptions').value;
    const options = type === 'dropdown'
      ? rawOpts.split('\n').map(s => s.trim()).filter(Boolean)
      : [];

    fetch('/features/api/columns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, type, options }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          bootstrap.Modal.getInstance(document.getElementById('addColumnModal')).hide();
          location.reload();
        }
      });
  }

  function deleteColumn(colId, colName, event) {
    event.stopPropagation();
    if (!confirm(`Delete column "${colName}"? All values in this column will be lost.`)) return;
    fetch(`/features/api/columns/${colId}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => { if (data.success) location.reload(); });
  }

  // ── Notes ────────────────────────────────────────────────────────────────────

  function openNotes(featureId, event) {
    event.stopPropagation();
    _notesFeatureId = featureId;
    document.getElementById('newNoteText').value = '';
    _loadNotes(featureId);
    bootstrap.Modal.getOrCreateInstance(document.getElementById('notesModal')).show();
  }

  function _loadNotes(featureId) {
    fetch(`/features/api/${featureId}/notes`)
      .then(r => r.json())
      .then(notes => {
        const container = document.getElementById('notesList');
        if (!notes.length) {
          container.innerHTML = '<p class="text-muted small">No notes yet.</p>';
          return;
        }
        container.innerHTML = notes.map(n => `
          <div class="note-item d-flex gap-2 mb-2" id="note-${n.id}">
            <div class="flex-grow-1">
              <textarea class="form-control form-control-sm note-text" rows="2" data-note-id="${n.id}">${_esc(n.note)}</textarea>
            </div>
            <div class="d-flex flex-column gap-1">
              <button class="btn btn-sm btn-outline-primary" onclick="FM.updateNote(${n.id})" title="Save note">
                <i class="bi bi-floppy"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" onclick="FM.deleteNote(${n.id})" title="Delete note">
                <i class="bi bi-trash3"></i>
              </button>
            </div>
          </div>`).join('');
      });
  }

  function addNote() {
    const text = document.getElementById('newNoteText').value.trim();
    if (!text || !_notesFeatureId) return;
    fetch(`/features/api/${_notesFeatureId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: text }),
    })
      .then(r => r.json())
      .then(() => {
        document.getElementById('newNoteText').value = '';
        _loadNotes(_notesFeatureId);
        _refreshNoteIcon(_notesFeatureId);
      });
  }

  function updateNote(noteId) {
    const ta = document.querySelector(`.note-text[data-note-id="${noteId}"]`);
    if (!ta) return;
    fetch(`/features/api/notes/${noteId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: ta.value }),
    });
  }

  function deleteNote(noteId) {
    if (!confirm('Delete this note?')) return;
    fetch(`/features/api/notes/${noteId}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(() => _loadNotes(_notesFeatureId));
  }

  function _refreshNoteIcon(featureId) {
    const row = document.getElementById(`row-${featureId}`);
    if (!row) return;
    const btn = row.querySelector('.btn-note-toggle');
    if (btn) btn.innerHTML = '<i class="bi bi-chat-text-fill text-primary"></i><span class="note-count">+</span>';
  }

  function _esc(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Public API
  return {
    openAddFeature, saveNewFeature, deleteFeature,
    openAddColumn, toggleColOptions, saveNewColumn, deleteColumn,
    openNotes, addNote, updateNote, deleteNote,
    clearFilters, exportFiltered,
  };
})();
