const API = 'http://localhost:8000';
let token = localStorage.getItem('token') || null;
let currentUser = JSON.parse(localStorage.getItem('user') || 'null');
const history = JSON.parse(localStorage.getItem('verifyHistory') || '[]');

// ── PAGE ROUTING ──────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`page-${name}`).classList.add('active');
  document.querySelectorAll('.nav-link').forEach(l => {
    if (l.getAttribute('onclick')?.includes(name)) l.classList.add('active');
  });
  if (name === 'history') renderHistory();
  if ((name === 'verify' || name === 'report') && !token) {
    showToast('Please login first.');
    showPage('auth');
  }
}

// ── AUTH TABS ─────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.auth-form').forEach(f => f.classList.add('hidden'));
  document.getElementById(`${tab}Form`).classList.remove('hidden');
  event.target.classList.add('active');
}

// ── VERIFY TABS ───────────────────────────────────────────────
function switchVerifyTab(tab) {
  document.querySelectorAll('.vtab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.vtab-content').forEach(c => c.classList.add('hidden'));
  document.getElementById(`vtab-${tab}`).classList.remove('hidden');
  event.target.classList.add('active');
  document.getElementById('verifyResult').classList.add('hidden');
}

// ── AUTH ──────────────────────────────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById('loginError');
  errEl.classList.add('hidden');
  try {
    const res = await api('POST', '/auth/login', {
      email: document.getElementById('loginEmail').value,
      password: document.getElementById('loginPassword').value,
    });
    saveAuth(res);
    showPage('home');
    showToast(`Welcome back, ${res.user.full_name} 👋`);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const errEl = document.getElementById('signupError');
  errEl.classList.add('hidden');
  try {
    const res = await api('POST', '/auth/signup', {
      email: document.getElementById('signupEmail').value,
      password: document.getElementById('signupPassword').value,
      full_name: document.getElementById('signupName').value,
      role: document.getElementById('signupRole').value,
    });
    saveAuth(res);
    showPage('home');
    showToast(`Account created! Welcome, ${res.user.full_name} 🎉`);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

function saveAuth(res) {
  token = res.access_token;
  currentUser = res.user;
  localStorage.setItem('token', token);
  localStorage.setItem('user', JSON.stringify(currentUser));
  updateNavAuth();
}

function updateNavAuth() {
  const badge = document.getElementById('userBadge');
  const btn = document.getElementById('authBtn');
  if (currentUser) {
    badge.textContent = `${currentUser.full_name} (${currentUser.role})`;
    badge.classList.remove('hidden');
    btn.textContent = 'Logout';
    btn.onclick = logout;
  } else {
    badge.classList.add('hidden');
    btn.textContent = 'Login';
    btn.onclick = () => showPage('auth');
  }
}

function logout() {
  token = null; currentUser = null;
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  updateNavAuth();
  showPage('home');
  showToast('Logged out.');
}

// ── VERIFICATION ──────────────────────────────────────────────
async function handleBarcodeVerify(e) {
  e.preventDefault();
  const barcode = document.getElementById('barcodeInput').value.trim();
  showLoader(true);
  try {
    const form = new FormData();
    form.append('barcode', barcode);
    const res = await apiFetch('POST', '/verify/barcode', form, true);
    showResult(res);
    saveHistory(res);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    showLoader(false);
  }
}

async function handleImageVerify(e) {
  e.preventDefault();
  const file = document.getElementById('imageInput').files[0];
  if (!file) { showToast('Please select an image.'); return; }
  showLoader(true);
  try {
    const form = new FormData();
    form.append('file', file);
    const res = await apiFetch('POST', '/verify/image', form, true);
    showResult(res);
    saveHistory(res);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    showLoader(false);
  }
}

function showResult(r) {
  const el = document.getElementById('verifyResult');
  const icons = { genuine: '✅', suspicious: '⚠️', fake: '🚨', unknown: '❓' };
  const scorePercent = Math.round(r.risk_score * 100);

  const flagsHtml = r.flags?.length
    ? `<div class="result-flags">
        <div class="result-flags-title">⚠ Anomalies Detected</div>
        ${r.flags.map(f => `<div class="flag-item">⚠ ${f}</div>`).join('')}
       </div>`
    : '';

  const ocrHtml = r.ocr_text
    ? `<div class="result-field" style="grid-column:1/-1">
        <div class="result-field-label">OCR Extracted Text</div>
        <div class="result-field-value" style="font-size:.8rem;font-weight:400;white-space:pre-wrap;max-height:100px;overflow:auto">${r.ocr_text}</div>
       </div>`
    : '';

  el.innerHTML = `
    <div class="result-header">
      <div class="result-status-icon">${icons[r.status] || '❓'}</div>
      <div>
        <div class="result-title">${capitalize(r.status)}</div>
        <div class="result-score">Risk Score: ${scorePercent}% ${riskBar(scorePercent)}</div>
      </div>
    </div>
    <div class="result-grid">
      <div class="result-field">
        <div class="result-field-label">Medicine Name</div>
        <div class="result-field-value">${r.medicine_name || '—'}</div>
      </div>
      <div class="result-field">
        <div class="result-field-label">Manufacturer</div>
        <div class="result-field-value">${r.manufacturer || '—'}</div>
      </div>
      <div class="result-field">
        <div class="result-field-label">Batch Number</div>
        <div class="result-field-value">${r.batch_number || '—'}</div>
      </div>
      <div class="result-field">
        <div class="result-field-label">Expiry Date</div>
        <div class="result-field-value">${r.expiry_date || '—'}</div>
      </div>
      <div class="result-field">
        <div class="result-field-label">Barcode</div>
        <div class="result-field-value">${r.barcode_value || '—'}</div>
      </div>
      ${ocrHtml}
    </div>
    ${flagsHtml}
    <div class="result-message ${r.status}">${r.message}</div>
  `;
  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function riskBar(pct) {
  const color = pct < 30 ? '#22c55e' : pct < 60 ? '#f59e0b' : '#ef4444';
  return `<span style="display:inline-block;width:80px;height:6px;background:#2a3347;border-radius:3px;vertical-align:middle;margin-left:6px">
    <span style="display:block;width:${pct}%;height:100%;background:${color};border-radius:3px"></span>
  </span>`;
}

// ── REPORT ────────────────────────────────────────────────────
async function handleReport(e) {
  e.preventDefault();
  const msgEl = document.getElementById('reportMsg');
  const errEl = document.getElementById('reportError');
  msgEl.classList.add('hidden');
  errEl.classList.add('hidden');
  try {
    await api('POST', '/reports/', {
      barcode: document.getElementById('reportBarcode').value || null,
      description: document.getElementById('reportDesc').value,
      location: document.getElementById('reportLocation').value || null,
    });
    msgEl.textContent = 'Report submitted. Thank you for helping keep medicines safe.';
    msgEl.classList.remove('hidden');
    e.target.reset();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

// ── HISTORY ───────────────────────────────────────────────────
function saveHistory(result) {
  history.unshift({ ...result, _ts: new Date().toLocaleString() });
  if (history.length > 50) history.pop();
  localStorage.setItem('verifyHistory', JSON.stringify(history));
}

function renderHistory() {
  const el = document.getElementById('historyList');
  if (!history.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>No verifications yet.</p></div>`;
    return;
  }
  const icons = { genuine: '✅', suspicious: '⚠️', fake: '🚨', unknown: '❓' };
  const colors = { genuine: 'rgba(34,197,94,.15)', suspicious: 'rgba(245,158,11,.15)', fake: 'rgba(239,68,68,.15)', unknown: 'rgba(139,149,168,.15)' };
  const textColors = { genuine: '#22c55e', suspicious: '#f59e0b', fake: '#ef4444', unknown: '#8b95a8' };

  el.innerHTML = history.map(h => `
    <div class="history-item">
      <div class="history-item-left">
        <div class="history-item-icon">${icons[h.status] || '❓'}</div>
        <div>
          <div class="history-item-name">${h.medicine_name || h.barcode_value || 'Unknown Medicine'}</div>
          <div class="history-item-meta">${h._ts} · Batch: ${h.batch_number || '—'}</div>
        </div>
      </div>
      <div class="history-item-right">
        <span class="score-pill" style="background:${colors[h.status]};color:${textColors[h.status]}">
          ${icons[h.status]} ${capitalize(h.status)} · ${Math.round(h.risk_score * 100)}%
        </span>
      </div>
    </div>
  `).join('');
}

// ── IMAGE PREVIEW ─────────────────────────────────────────────
function previewImage(e) {
  const file = e.target.files[0];
  if (!file) return;
  const preview = document.getElementById('imagePreview');
  preview.src = URL.createObjectURL(file);
  preview.classList.remove('hidden');
}

// ── API HELPERS ───────────────────────────────────────────────
async function api(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`Server error (${res.status}): ${text.slice(0, 120)}`); }
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

async function apiFetch(method, path, formData) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`Server error (${res.status}): ${text.slice(0, 120)}`); }
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

// ── UTILS ─────────────────────────────────────────────────────
function showLoader(show) {
  document.getElementById('verifyLoader').classList.toggle('hidden', !show);
  document.getElementById('verifyResult').classList.add('hidden');
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3000);
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

// ── INIT ──────────────────────────────────────────────────────
updateNavAuth();
