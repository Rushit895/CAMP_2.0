'use strict';

// Same-origin when served by FastAPI; fall back to local dev port if opened as a file.
const API_BASE = location.protocol.startsWith('http')
  ? location.origin + '/api'
  : 'http://127.0.0.1:8099/api';

const POS = Array.from({ length: 12 }, (_, i) => 'PO' + (i + 1));
const BLOOM = { 1: 'Remember', 2: 'Understand', 3: 'Apply', 4: 'Analyze', 5: 'Evaluate', 6: 'Create' };

const $ = (id) => document.getElementById(id);
let lastMatrix = null; // cache of the last /map response for drawer lookups

const SAMPLE = [
  'Apply data structures and algorithms to solve computational problems efficiently.',
  'Analyze the time complexity and space complexity of algorithms.',
  'Design and develop a software system using modern engineering tools.',
  'Evaluate the environmental impact and sustainability of engineering solutions.',
  'Communicate technical results effectively through reports and presentations.',
  'Work effectively as a member of a multidisciplinary project team.',
].join('\n');

// ---- Theme ----------------------------------------------------------------
function initTheme() {
  const saved = localStorage.getItem('camp-theme');
  const theme = saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(theme);
}
function setTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('camp-theme', t);
  $('themeToggle').textContent = t === 'dark' ? '☀' : '☾';
}
$('themeToggle').addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme');
  setTheme(cur === 'dark' ? 'light' : 'dark');
});

// ---- API health -----------------------------------------------------------
async function checkHealth() {
  const pill = $('apiStatus');
  try {
    const r = await fetch(API_BASE + '/health');
    if (!r.ok) throw new Error();
    const j = await r.json();
    pill.textContent = j.algorithm + ' online';
    pill.className = 'pill pill-ok';
  } catch {
    pill.textContent = 'API offline';
    pill.className = 'pill pill-bad';
  }
}

// ---- Mapping --------------------------------------------------------------
async function runMapping() {
  const err = $('inputError');
  err.hidden = true;
  const cos = $('cosInput').value.split('\n').map((s) => s.trim()).filter(Boolean);
  if (cos.length === 0) {
    err.textContent = 'Enter at least one Course Outcome.';
    err.hidden = false;
    return;
  }

  const btn = $('mapBtn');
  btn.disabled = true;
  btn.textContent = 'Mapping…';
  try {
    const r = await fetch(API_BASE + '/map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cos }),
    });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      throw new Error(body.detail || ('HTTP ' + r.status));
    }
    const data = await r.json();
    lastMatrix = data.matrix;
    renderMatrix(data.matrix);
  } catch (e) {
    err.textContent = 'Mapping failed: ' + e.message;
    err.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Map to POs';
  }
}

// ---- Persistence: save / load / delete -----------------------------------
function toast(msg, isErr) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast' + (isErr ? ' toast-err' : '');
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, 3200);
}

async function refreshSaved(selected) {
  try {
    const r = await fetch(API_BASE + '/courses');
    if (!r.ok) return;
    const courses = await r.json();
    const sel = $('savedCourses');
    sel.innerHTML = '<option value="">— saved courses —</option>' +
      courses.map((c) => '<option value="' + escapeHtml(c.code) + '">' +
        escapeHtml(c.code + ' · ' + c.title) + ' (' + c.co_count + ' CO)</option>').join('');
    if (selected) sel.value = selected;
    $('deleteCourse').hidden = !sel.value;
  } catch { /* API offline — leave dropdown as-is */ }
}

async function saveCourse() {
  const code = $('courseCode').value.trim();
  const title = $('courseTitle').value.trim();
  const cos = $('cosInput').value.split('\n').map((s) => s.trim()).filter(Boolean);
  if (!code || !title) return toast('Course code and title are required to save.', true);
  if (cos.length === 0) return toast('Enter at least one Course Outcome.', true);

  const btn = $('saveBtn');
  btn.disabled = true;
  try {
    const r = await fetch(API_BASE + '/courses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, title, cos }),
    });
    if (!r.ok) {
      const b = await r.json().catch(() => ({}));
      throw new Error(b.detail || ('HTTP ' + r.status));
    }
    const data = await r.json();
    lastMatrix = data.matrix;
    renderMatrix(data.matrix);
    await refreshSaved(code);
    toast('Saved “' + code + '” with its CO·PO matrix.');
  } catch (e) {
    toast('Save failed: ' + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

async function loadCourse(code) {
  if (!code) { $('deleteCourse').hidden = true; return; }
  try {
    const r = await fetch(API_BASE + '/courses/' + encodeURIComponent(code));
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    $('courseCode').value = data.code;
    $('courseTitle').value = data.title;
    $('cosInput').value = data.matrix.map((row) => row.co).join('\n');
    lastMatrix = data.matrix;
    renderMatrix(data.matrix);
    $('deleteCourse').hidden = false;
    toast('Loaded “' + data.code + '”.');
  } catch (e) {
    toast('Load failed: ' + e.message, true);
  }
}

async function deleteCourse() {
  const code = $('savedCourses').value;
  if (!code) return;
  if (!confirm('Delete course “' + code + '” and its stored matrix?')) return;
  try {
    const r = await fetch(API_BASE + '/courses/' + encodeURIComponent(code), { method: 'DELETE' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    await refreshSaved();
    toast('Deleted “' + code + '”.');
  } catch (e) {
    toast('Delete failed: ' + e.message, true);
  }
}

function renderMatrix(matrix) {
  $('emptyState').hidden = true;
  $('matrixWrap').hidden = false;

  const code = $('courseCode').value.trim();
  const title = $('courseTitle').value.trim();
  $('resultMeta').textContent = [code, title].filter(Boolean).join(' · ') ||
    (matrix.length + ' CO' + (matrix.length > 1 ? 's' : ''));

  // Header
  const thead = $('matrix').querySelector('thead');
  thead.innerHTML =
    '<tr><th class="co-col">Course Outcome</th>' +
    POS.map((p) => '<th>' + p + '</th>').join('') + '</tr>';

  // Body
  const tbody = $('matrix').querySelector('tbody');
  tbody.innerHTML = '';
  const totals = Object.fromEntries(POS.map((p) => [p, 0]));

  matrix.forEach((row, ri) => {
    const tr = document.createElement('tr');

    const coTd = document.createElement('td');
    coTd.className = 'co-cell';
    coTd.innerHTML =
      '<div class="co-name">CO' + (ri + 1) + '</div>' +
      '<div class="co-text">' + escapeHtml(row.co) + '</div>' +
      '<span class="bloom-badge">Bloom ' + row.bloom_level + ' · ' + BLOOM[row.bloom_level] + '</span>';
    tr.appendChild(coTd);

    POS.forEach((p) => {
      const lvl = row.pos[p] ?? 0;
      totals[p] += lvl;
      const td = document.createElement('td');
      const cell = document.createElement('div');
      cell.className = 'cell lvl-' + lvl;
      cell.textContent = lvl === 0 ? '·' : lvl;
      cell.tabIndex = 0;
      cell.setAttribute('role', 'button');
      cell.title = 'CO' + (ri + 1) + ' → ' + p + ' (click for detail)';
      const open = () => openDrawer(ri, p);
      cell.addEventListener('click', open);
      cell.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
      td.appendChild(cell);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  // Average attainment row
  const avg = document.createElement('tr');
  avg.className = 'avg-row';
  avg.innerHTML = '<td class="co-cell">Average attainment</td>' +
    POS.map((p) => '<td><div class="avg-val">' +
      (totals[p] / matrix.length).toFixed(1) + '</div></td>').join('');
  tbody.appendChild(avg);
}

// ---- Drawer ---------------------------------------------------------------
function openDrawer(rowIdx, po) {
  const row = lastMatrix[rowIdx];
  const cell = row.details.find((d) => d.po === po);
  if (!cell) return;

  $('drawerTitle').textContent = 'CO' + (rowIdx + 1) + ' → ' + po;

  const pct = (x) => Math.round(Math.max(0, Math.min(1, x)) * 100);
  const terms = cell.matched_terms || [];
  const termsHtml = terms.length
    ? terms.map((t) => '<div class="term-row"><span>' + escapeHtml(t.term) +
        '</span><span class="term-w">' + t.weight.toFixed(2) + '</span></div>').join('')
    : '<p class="no-terms">No lexicon terms matched — score comes from descriptor similarity only.</p>';

  $('drawerBody').innerHTML =
    '<div class="d-level">' +
      '<div class="cell lvl-' + cell.level + '">' + (cell.level || '·') + '</div>' +
      '<div><div class="d-level-label">' + cell.label + '</div>' +
      '<div class="d-level-sub">' + cell.title + '</div></div>' +
    '</div>' +
    '<div class="rationale">' + escapeHtml(cell.rationale) + '</div>' +
    '<div class="metrics">' +
      metric('Semantic (σ)', cell.semantic, pct(cell.semantic)) +
      metric('Lexical (λ)', cell.lexical, pct(cell.lexical)) +
      metric('Bloom gate', cell.gate, pct(cell.gate)) +
      metric('Raw score', cell.raw, pct(cell.raw)) +
    '</div>' +
    '<p class="terms-title">Matched lexicon terms</p>' + termsHtml;

  $('drawer').hidden = false;
  $('scrim').hidden = false;
}
function metric(label, val, pct) {
  return '<div class="metric"><div class="metric-k">' + label + '</div>' +
    '<div class="metric-v">' + val.toFixed(3) + '</div>' +
    '<div class="bar"><span style="width:' + pct + '%"></span></div></div>';
}
function closeDrawer() { $('drawer').hidden = true; $('scrim').hidden = true; }

// ---- Utils & wiring -------------------------------------------------------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

$('mapBtn').addEventListener('click', runMapping);
$('saveBtn').addEventListener('click', saveCourse);
$('savedCourses').addEventListener('change', (e) => loadCourse(e.target.value));
$('deleteCourse').addEventListener('click', deleteCourse);
$('clearBtn').addEventListener('click', () => {
  $('cosInput').value = '';
  $('matrixWrap').hidden = true;
  $('emptyState').hidden = false;
  $('inputError').hidden = true;
  $('savedCourses').value = '';
  $('deleteCourse').hidden = true;
  lastMatrix = null;
});
$('loadSample').addEventListener('click', () => { $('cosInput').value = SAMPLE; });
$('drawerClose').addEventListener('click', closeDrawer);
$('scrim').addEventListener('click', closeDrawer);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

initTheme();
checkHealth();
refreshSaved();
