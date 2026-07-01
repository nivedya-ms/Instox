// Shared utilities: API calls, auth, formatting, toast.

const API_BASE = '/api';

async function api(path, options = {}) {
  const opts = {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  };
  if (opts.body && typeof opts.body !== 'string') {
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(API_BASE + path, opts);
  if (res.status === 401) {
    if (!location.pathname.endsWith('/login.html') && !location.pathname.endsWith('/register.html')) {
      location.href = '/login.html';
    }
    throw new Error('Unauthorized');
  }
  let body = null;
  try { body = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok || (body && body.success === false)) {
    const msg = (body && (body.error || body.message)) || `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

function fmtMoney(n) {
  if (n === null || n === undefined) return '—';
  return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function toast(msg, type) {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  if (type === 'error') el.style.background = '#dc2626';
  else if (type === 'success') el.style.background = '#16a34a';
  else el.style.background = '#0f172a';
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove('show'), 2500);
}

function showAlert(containerId, msg, type) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!msg) { el.innerHTML = ''; return; }
  el.innerHTML = `<div class="alert ${type || 'error'}">${escapeHtml(msg)}</div>`;
}

function escapeHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function debounce(fn, ms) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), ms);
  };
}

async function requireAuth() {
  try {
    const r = await api('/auth/me');
    return r.data;
  } catch (e) {
    return null;
  }
}

function renderNavbar(user) {
  const nav = document.getElementById('navbar');
  if (!nav) return;
  const shop = user && user.shop_name ? escapeHtml(user.shop_name) : '';
  nav.innerHTML = `
    <a href="/" class="brand">Instox</a>
    <div class="nav-actions">
      <span class="shop-name">${shop}</span>
      <a href="#" id="logout-btn">Logout</a>
    </div>`;
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try { await api('/auth/logout', { method: 'POST' }); } catch (_) {}
      location.href = '/login.html';
    });
  }
}

function renderBottomNav(active) {
  const nav = document.getElementById('bottom-nav');
  if (!nav) return;
  const items = [
    { key: 'home', href: '/', label: 'Home', icon: '🏠' },
    { key: 'products', href: '/products.html', label: 'Products', icon: '📦' },
    { key: 'billing', href: '/billing.html', label: 'Bill', icon: '🛒' },
    { key: 'sales', href: '/sales.html', label: 'Sales', icon: '📋' },
    { key: 'purchase', href: '/purchase_list.html', label: 'To Buy', icon: '✅' },
  ];
  nav.innerHTML = items
    .map(
      (i) =>
        `<a href="${i.href}" class="${i.key === active ? 'active' : ''}"><span class="icon">${i.icon}</span>${i.label}</a>`
    )
    .join('');
}

async function bootstrapPage({ active } = {}) {
  const user = await requireAuth();
  if (!user) return null;
  renderNavbar(user);
  renderBottomNav(active);
  return user;
}

window.Instox = {
  api,
  fmtMoney,
  fmtDate,
  fmtDateTime,
  toast,
  showAlert,
  escapeHtml,
  debounce,
  requireAuth,
  bootstrapPage,
};
