/**
 * Dashboard: Chart.js charts + DataTables feature overview table.
 */
document.addEventListener('DOMContentLoaded', () => {
  _initCharts();
  _initTable();
  _initFilters();
});

// ── Color palettes ─────────────────────────────────────────────────────────────

const PALETTE = {
  status: {
    'GA': '#107C10',
    'Rolling Out': '#0078D4',
    'In Development': '#C39500',
    'Unknown': '#8A8886',
  },
  phase: {
    'General Availability': '#107C10',
    'Targeted Release': '#C39500',
    'Preview': '#0078D4',
    'Frontier': '#8764B8',
    'Unknown': '#8A8886',
  },
  readiness: {
    'Safe to Promote': '#107C10',
    'Pilot Only': '#C39500',
    'Do Not Commit': '#D13438',
    'Unknown': '#8A8886',
  },
  confidence: {
    'High': '#107C10',
    'Medium': '#C39500',
    'Low': '#D13438',
    'Unknown': '#8A8886',
  },
};

const CHART_DEFAULTS = {
  plugins: {
    legend: {
      position: 'bottom',
      labels: { boxWidth: 12, padding: 12, font: { size: 11 } },
    },
  },
  animation: { duration: 400 },
};

// ── Charts ─────────────────────────────────────────────────────────────────────

function _initCharts() {
  fetch('/api/chart-data')
    .then(r => r.json())
    .then(data => {
      _donut('chartStatus', data.status, PALETTE.status);
      _donut('chartPhase', data.phase, PALETTE.phase);
      _donut('chartReadiness', data.readiness, PALETTE.readiness);
      _donut('chartConfidence', data.confidence, PALETTE.confidence);
      _barTimeline('chartGaTimeline', data.ga_timeline);
      _barWorkload('chartWorkload', data.workload);
    })
    .catch(() => {/* charts optional if no data */});
}

function _donut(canvasId, dataObj, palette) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const labels = Object.keys(dataObj);
  const values = Object.values(dataObj);
  if (!labels.length) return;
  const colors = labels.map(l => palette[l] || '#8A8886');

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }],
    },
    options: {
      ...CHART_DEFAULTS,
      cutout: '60%',
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} (${Math.round(ctx.parsed / ctx.chart.data.datasets[0].data.reduce((a, b) => a + b, 0) * 100)}%)`,
          },
        },
      },
    },
  });
}

function _barTimeline(canvasId, dataObj) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  // Sort by approximate date order
  const sorted = Object.entries(dataObj).sort(([a], [b]) => _sortDate(a) - _sortDate(b));
  const labels = sorted.map(([k]) => k);
  const values = sorted.map(([, v]) => v);
  if (!labels.length) return;

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Features reaching GA',
        data: values,
        backgroundColor: '#0078D4',
        borderRadius: 4,
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,.06)' },
        },
        x: { ticks: { font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

function _barWorkload(canvasId, dataObj) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const sorted = Object.entries(dataObj).sort(([, a], [, b]) => b - a).slice(0, 12);
  const labels = sorted.map(([k]) => k);
  const values = sorted.map(([, v]) => v);

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Features',
        data: values,
        backgroundColor: '#106EBE',
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display: false },
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,.06)' },
        },
        y: { ticks: { font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

function _sortDate(str) {
  const months = ['january','february','march','april','may','june','july','august','september','october','november','december'];
  const qm = str.match(/Q([1-4])\s*(\d{4})/i);
  if (qm) return parseInt(qm[2]) * 12 + (parseInt(qm[1]) - 1) * 3;
  const mm = str.toLowerCase().match(/(\w+)\s+(\d{4})/);
  if (mm) {
    const mi = months.indexOf(mm[1]);
    if (mi >= 0) return parseInt(mm[2]) * 12 + mi;
  }
  return 9999 * 12;
}

// ── DataTable ─────────────────────────────────────────────────────────────────

function _initTable() {
  if (!document.getElementById('dashboardTable')) return;
  $('#dashboardTable').DataTable({
    pageLength: 25,
    lengthMenu: [10, 25, 50, 100],
    order: [[2, 'asc'], [0, 'asc']],
    columnDefs: [{ orderable: false, targets: [] }],
    language: {
      search: '',
      searchPlaceholder: 'Search features…',
      info: 'Showing _START_ to _END_ of _TOTAL_ features',
    },
    dom: "<'row align-items-center mb-2'<'col-sm-6'l><'col-sm-6'f>>rt<'row mt-2'<'col-sm-6'i><'col-sm-6'p>>",
  });
}

// ── Multi-select filters (Tom Select) ─────────────────────────────────────────

const DASH_FILTERS = [
  { elId: 'filterWorkload',   dataKey: 'workload' },
  { elId: 'filterStatus',     dataKey: 'status' },
  { elId: 'filterPhase',      dataKey: 'phase' },
  { elId: 'filterGaEstimate', dataKey: 'ga' },
  { elId: 'filterReadiness',  dataKey: 'readiness' },
];

const _dashTS = {};

function _initFilters() {
  DASH_FILTERS.forEach(({ elId }) => {
    const el = document.getElementById(elId);
    if (!el) return;
    _dashTS[elId] = new TomSelect(el, {
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
  DASH_FILTERS.forEach(({ elId, dataKey }) => {
    const ts = _dashTS[elId];
    const vals = ts ? [].concat(ts.getValue()).filter(Boolean) : [];
    selected[dataKey] = vals;
    if (vals.length) anyActive = true;
  });

  const clearBtn = document.getElementById('clearFiltersBtn');
  if (clearBtn) clearBtn.style.display = anyActive ? '' : 'none';

  document.querySelectorAll('#dashboardTable tbody tr.feature-row').forEach(row => {
    const ok = DASH_FILTERS.every(({ dataKey }) => {
      const vals = selected[dataKey];
      return !vals.length || vals.includes(row.dataset[dataKey] || '');
    });
    row.style.display = ok ? '' : 'none';
  });
}

function clearDashFilters() {
  Object.values(_dashTS).forEach(ts => ts.clear());
  _applyFilters();
}

function exportFiltered() {
  const paramMap = {
    filterWorkload:   'workload',
    filterStatus:     'status',
    filterPhase:      'phase',
    filterGaEstimate: 'ga',
    filterReadiness:  'readiness',
  };
  const params = new URLSearchParams();
  for (const [elId, param] of Object.entries(paramMap)) {
    const ts = _dashTS[elId];
    if (ts) [].concat(ts.getValue()).filter(Boolean).forEach(v => params.append(param, v));
  }
  window.location.href = '/export/excel?' + params.toString();
}
