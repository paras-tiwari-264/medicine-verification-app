const API = 'http://localhost:8000';
let adminToken = sessionStorage.getItem('adminToken') || null;
let adminUser  = JSON.parse(sessionStorage.getItem('adminUser') || 'null');

// ── INIT ─────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  if (adminToken && adminUser?.role === 'admin') {
    showDashboard();
    loadOverview();
  }
});

// ── LOGIN ─────────────────────────────────────────────────────
async function handleAdminLogin(e) {
  e.preventDefault();
  const errEl  = document.getElementById('loginError');
  const btn    = document.getElementById('loginBtn');
  const btnTxt = document.getElementById('loginBtnText');
  const spin   = document.getElementById('loginSpinner');
  errEl.classList.add('hidden');

  const email    = document.getElementById('adminEmail').value.trim();
  const password = document.getElementById('adminPassword').value;

  btn.disabled = true;
  btnTxt.textContent = 'Signing in...';
  spin.classList.remove('hidden');

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed.');
    if (data.user.role !== 'admin') throw new Error('Access denied. Admin credentials required.');

    adminToken = data.access_token;
    adminUser  = data.user;
    sessionStorage.setItem('adminToken', adminToken);
    sessionStorage.setItem('adminUser', JSON.stringify(adminUser));

    showDashboard();
    loadOverview();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btnTxt.textContent = 'Sign In to Admin Panel';
    spin.classList.add('hidden');
  }
}

function showDashboard() {
  document.getElementById('loginScreen').classList.add('hidden');
  document.getElementById('dashboard').classList.remove('hidden');
  document.getElementById('sidebarUser').textContent = adminUser?.full_name || adminUser?.email || 'Admin';
  document.getElementById('topbarName').textContent  = adminUser?.full_name || '';
}

function adminLogout() {
  sessionStorage.removeItem('adminToken');
  sessionStorage.removeItem('adminUser');
  adminToken = null; adminUser = null;
  document.getElementById('dashboard').classList.add('hidden');
  document.getElementById('loginScreen').classList.remove('hidden');
}

// ── NAVIGATION ────────────────────────────────────────────────
const sectionTitles = {
  overview: 'Dashboard', medicines: 'Medicines',
  reports: 'Reports', users: 'Users',
  pharmacies: 'Pharmacies', verifications: 'Activity',
};

function showSection(name, btn) {
  document.querySelectorAll('.dsection').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`section-${name}`).classList.add('active');
  if (btn) btn.classList.add('active');
  document.getElementById('topbarTitle').textContent = sectionTitles[name] || name;

  const loaders = { medicines: loadMedicines, reports: loadReports, users: loadUsers, pharmacies: loadPharmacies, verifications: loadVerifications, overview: loadOverview };
  if (loaders[name]) loaders[name]();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── API HELPER ────────────────────────────────────────────────
async function adminApi(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${adminToken}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`Server error (${res.status})`); }
  if (!res.ok) throw new Error(data.detail || 'Request failed.');
  return data;
}

// ── OVERVIEW ──────────────────────────────────────────────────
async function loadOverview() {
  try {
    const [stats, reports, activity] = await Promise.all([
      adminApi('GET', '/admin/stats'),
      adminApi('GET', '/reports/'),
      adminApi('GET', '/admin/verifications?limit=5'),
    ]);

    document.getElementById('statMedicines').textContent     = stats.total_medicines;
    document.getElementById('statUsers').textContent         = stats.total_users;
    document.getElementById('statVerifications').textContent = stats.total_verifications;
    document.getElementById('statReports').textContent       = stats.total_reports;
    document.getElementById('statPending').textContent       = stats.pending_reports;
    document.getElementById('statPharmacies').textContent    = stats.total_pharmacies ?? '—';
    document.getElementById('pendingBadge').textContent      = stats.pending_reports;

    // Recent reports
    const rEl = document.getElementById('recentReports');
    const recent = reports.slice(0, 5);
    rEl.innerHTML = recent.length
      ? recent.map(r => `
          <div class="panel-item">
            <div class="panel-item-title">${r.description?.slice(0, 60) || 'No description'}...</div>
            <div class="panel-item-sub">${statusPill(r.status)} · ${fmtDate(r.created_at)}</div>
          </div>`).join('')
      : '<div class="panel-item"><div class="panel-item-sub">No reports yet.</div></div>';

    // Recent activity
    const aEl = document.getElementById('recentActivity');
    aEl.innerHTML = activity.length
      ? activity.map(v => `
          <div class="panel-item">
            <div class="panel-item-title">${v.medicine_name || v.batch_number || 'Unknown'}</div>
            <div class="panel-item-sub">${statusPill(v.status)} · Risk ${Math.round((v.risk_score||0)*100)}% · ${fmtDate(v.timestamp)}</div>
          </div>`).join('')
      : '<div class="panel-item"><div class="panel-item-sub">No activity yet.</div></div>';
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ── MEDICINES ─────────────────────────────────────────────────
async function loadMedicines() {
  const tbody = document.getElementById('medicinesTable');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text2);padding:2rem">Loading...</td></tr>';
  try {
    const meds = await adminApi('GET', '/medicines/');
    if (!meds.length) { tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No medicines in database.</td></tr>'; return; }
    tbody.innerHTML = meds.map(m => `
      <tr>
        <td><strong>${m.name}</strong>${m.dosage_form ? `<br><span style="font-size:.75rem;color:var(--text2)">${m.dosage_form}</span>` : ''}</td>
        <td>${m.manufacturer}</td>
        <td><code style="font-size:.8rem;background:var(--bg3);padding:.1rem .4rem;border-radius:4px">${m.batch_number}</code></td>
        <td>${m.expiry_date}</td>
        <td>${medStatusPill(m.status, m.is_approved)}</td>
        <td>
          <button class="tbl-btn edit" onclick="editMedicine(${JSON.stringify(m).replace(/"/g,'&quot;')})">Edit</button>
          <button class="tbl-btn del" onclick="confirmDelete('medicine','${m.id}','${m.name}')">Delete</button>
        </td>
      </tr>`).join('');
  } catch (err) { toast(err.message, 'error'); }
}

function medStatusPill(status, is_approved) {
  if (!is_approved || status === 'banned') return '<span class="pill pill-red">Banned</span>';
  if (status === 'recalled') return '<span class="pill pill-yellow">Recalled</span>';
  return '<span class="pill pill-green">Approved</span>';
}

function openMedicineModal(med) {
  document.getElementById('modalTitle').textContent = med ? 'Edit Medicine' : 'Add Medicine';
  document.getElementById('modalSaveBtn').textContent = med ? 'Update Medicine' : 'Save Medicine';
  document.getElementById('medicineId').value   = med?.id || '';
  document.getElementById('mName').value        = med?.name || '';
  document.getElementById('mManufacturer').value= med?.manufacturer || '';
  document.getElementById('mBatch').value       = med?.batch_number || '';
  document.getElementById('mExpiry').value      = med?.expiry_date || '';
  document.getElementById('mMfgDate').value     = med?.manufacturing_date || '';
  document.getElementById('mDosage').value      = med?.dosage_form || '';
  document.getElementById('mComposition').value = med?.composition || '';
  document.getElementById('mPackaging').value   = med?.approved_packaging || '';
  document.getElementById('mStatus').value      = med?.status || 'approved';
  document.getElementById('modalError').classList.add('hidden');
  document.getElementById('medicineModal').classList.remove('hidden');
}

function editMedicine(med) { openMedicineModal(med); }

function closeMedicineModal(e) {
  if (e && e.target !== document.getElementById('medicineModal')) return;
  document.getElementById('medicineModal').classList.add('hidden');
}

async function saveMedicine(e) {
  e.preventDefault();
  const errEl = document.getElementById('modalError');
  errEl.classList.add('hidden');
  const id = document.getElementById('medicineId').value;
  const payload = {
    name:               document.getElementById('mName').value.trim(),
    manufacturer:       document.getElementById('mManufacturer').value.trim(),
    batch_number:       document.getElementById('mBatch').value.trim(),
    expiry_date:        document.getElementById('mExpiry').value.trim(),
    manufacturing_date: document.getElementById('mMfgDate').value.trim() || null,
    dosage_form:        document.getElementById('mDosage').value || null,
    composition:        document.getElementById('mComposition').value.trim() || null,
    approved_packaging: document.getElementById('mPackaging').value.trim() || null,
    status:             document.getElementById('mStatus').value,
  };
  try {
    if (id) {
      await adminApi('PATCH', `/medicines/${id}`, payload);
      toast('Medicine updated.', 'success');
    } else {
      await adminApi('POST', '/medicines/', payload);
      toast('Medicine added.', 'success');
    }
    document.getElementById('medicineModal').classList.add('hidden');
    loadMedicines();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

// ── REPORTS ───────────────────────────────────────────────────
async function loadReports() {
  const container = document.getElementById('reportsList');
  container.innerHTML = '<div style="color:var(--text2);padding:1rem">Loading...</div>';
  const filter = document.getElementById('reportFilter')?.value || '';
  try {
    let reports = await adminApi('GET', '/reports/');
    if (filter) reports = reports.filter(r => r.status === filter);
    if (!reports.length) { container.innerHTML = '<div style="color:var(--text2);padding:1rem">No reports found.</div>'; return; }
    container.innerHTML = reports.map(r => `
      <div class="report-card">
        <div class="report-card-header">
          <div>
            <div class="report-card-title">
              ${r.batch_number ? `Batch: <code style="font-size:.8rem">${r.batch_number}</code>` : 'No batch specified'}
            </div>
            <div class="report-card-meta">Reported ${fmtDate(r.created_at)} · Location: ${r.location || 'Not specified'}</div>
          </div>
          ${statusPill(r.status)}
        </div>
        <div class="report-card-desc">${r.description}</div>
        <div class="report-card-actions">
          ${['pending','reviewed','resolved','dismissed'].map(s =>
            `<button class="status-btn ${r.status===s?'active-status':''}" onclick="updateReportStatus('${r.id}','${s}',this)">${capitalize(s)}</button>`
          ).join('')}
        </div>
      </div>`).join('');
  } catch (err) { toast(err.message, 'error'); }
}

async function updateReportStatus(id, status, btn) {
  try {
    await adminApi('PATCH', `/reports/${id}/status?new_status=${status}`);
    toast(`Report marked as ${status}.`, 'success');
    loadReports();
    loadOverview();
  } catch (err) { toast(err.message, 'error'); }
}

// ── USERS ─────────────────────────────────────────────────────
async function loadUsers() {
  const tbody = document.getElementById('usersTable');
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text2);padding:2rem">Loading...</td></tr>';
  try {
    const users = await adminApi('GET', '/admin/users');
    if (!users.length) { tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No users found.</td></tr>'; return; }
    tbody.innerHTML = users.map(u => `
      <tr>
        <td><strong>${u.full_name}</strong></td>
        <td style="color:var(--text2)">${u.email}</td>
        <td>${rolePill(u.role)}</td>
        <td style="color:var(--text2);font-size:.8rem">${fmtDate(u.created_at)}</td>
        <td>${u.role !== 'admin' ? `<button class="tbl-btn del" onclick="confirmDelete('user','${u.uid}','${u.full_name}')">Delete</button>` : '<span style="color:var(--text3);font-size:.75rem">Protected</span>'}</td>
      </tr>`).join('');
  } catch (err) { toast(err.message, 'error'); }
}

function rolePill(role) {
  const map = { admin: 'pill-red', pharmacy: 'pill-blue', user: 'pill-gray' };
  return `<span class="pill ${map[role]||'pill-gray'}">${capitalize(role)}</span>`;
}

// ── PHARMACIES ────────────────────────────────────────────────
async function loadPharmacies() {
  const tbody = document.getElementById('pharmaciesTable');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text2);padding:2rem">Loading...</td></tr>';
  try {
    const pharmacies = await adminApi('GET', '/pharmacy/');
    if (!pharmacies.length) { tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No pharmacies registered.</td></tr>'; return; }
    tbody.innerHTML = pharmacies.map(p => `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td><code style="font-size:.8rem;background:var(--bg3);padding:.1rem .4rem;border-radius:4px">${p.license_number}</code></td>
        <td style="color:var(--text2);font-size:.82rem">${p.address}</td>
        <td style="color:var(--text2);font-size:.82rem">${p.contact_email}</td>
        <td>${p.is_verified ? '<span class="pill pill-green">Verified</span>' : '<span class="pill pill-yellow">Pending</span>'}</td>
        <td>${!p.is_verified ? `<button class="tbl-btn verify-btn" onclick="verifyPharmacy('${p.id}')">Verify</button>` : ''}</td>
      </tr>`).join('');
  } catch (err) { toast(err.message, 'error'); }
}

async function verifyPharmacy(id) {
  try {
    await adminApi('PATCH', `/pharmacy/${id}/verify`);
    toast('Pharmacy verified.', 'success');
    loadPharmacies();
  } catch (err) { toast(err.message, 'error'); }
}

// ── VERIFICATIONS ─────────────────────────────────────────────
async function loadVerifications() {
  const tbody = document.getElementById('verificationsTable');
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text2);padding:2rem">Loading...</td></tr>';
  try {
    const items = await adminApi('GET', '/admin/verifications?limit=100');
    if (!items.length) { tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No verifications yet.</td></tr>'; return; }
    tbody.innerHTML = items.map(v => `
      <tr>
        <td><strong>${v.medicine_name || '—'}</strong></td>
        <td><code style="font-size:.8rem;background:var(--bg3);padding:.1rem .4rem;border-radius:4px">${v.batch_number || '—'}</code></td>
        <td>${statusPill(v.status)}</td>
        <td>
          <div style="display:flex;align-items:center;gap:.5rem">
            <span style="font-size:.82rem;font-weight:600">${Math.round((v.risk_score||0)*100)}%</span>
            <span style="display:inline-block;width:60px;height:5px;background:var(--bg4);border-radius:3px;overflow:hidden">
              <span style="display:block;width:${Math.round((v.risk_score||0)*100)}%;height:100%;background:${riskColor(v.risk_score)};border-radius:3px"></span>
            </span>
          </div>
        </td>
        <td style="color:var(--text2);font-size:.8rem">${fmtDate(v.timestamp)}</td>
      </tr>`).join('');
  } catch (err) { toast(err.message, 'error'); }
}

// ── DELETE CONFIRM ────────────────────────────────────────────
let _confirmCb = null;

function confirmDelete(type, id, name) {
  document.getElementById('confirmTitle').textContent = `Delete ${capitalize(type)}`;
  document.getElementById('confirmMsg').textContent   = `Are you sure you want to delete "${name}"? This cannot be undone.`;
  document.getElementById('confirmModal').classList.remove('hidden');
  _confirmCb = async () => {
    try {
      const path = type === 'medicine' ? `/medicines/${id}` : `/admin/users/${id}`;
      await adminApi('DELETE', path);
      toast(`${capitalize(type)} deleted.`, 'success');
      closeConfirm();
      if (type === 'medicine') loadMedicines();
      else loadUsers();
    } catch (err) { toast(err.message, 'error'); closeConfirm(); }
  };
  document.getElementById('confirmOkBtn').onclick = _confirmCb;
}

function closeConfirm(e) {
  if (e && e.target !== document.getElementById('confirmModal')) return;
  document.getElementById('confirmModal').classList.add('hidden');
  _confirmCb = null;
}

// ── HELPERS ───────────────────────────────────────────────────
function statusPill(status) {
  const map = {
    genuine:   'pill-green',  approved: 'pill-green',
    suspicious:'pill-yellow', pending:  'pill-yellow', reviewed: 'pill-yellow',
    fake:      'pill-red',    banned:   'pill-red',    dismissed:'pill-red',
    resolved:  'pill-blue',   recalled: 'pill-yellow',
    unknown:   'pill-gray',
  };
  return `<span class="pill ${map[status]||'pill-gray'}">${capitalize(status||'unknown')}</span>`;
}

function riskColor(score) {
  if (score < 0.3) return '#10b981';
  if (score < 0.6) return '#f59e0b';
  return '#ef4444';
}

function fmtDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }); }
  catch { return iso.slice(0, 10); }
}

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }

function toast(msg, type = '') {
  const el = document.getElementById('adminToast');
  el.textContent = msg;
  el.className = `admin-toast ${type}`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 3500);
}
