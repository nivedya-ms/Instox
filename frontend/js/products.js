(async () => {
  const user = await Instox.bootstrapPage({ active: 'products' });
  if (!user) return;

  const listEl = document.getElementById('product-list');
  const emptyEl = document.getElementById('empty');
  const searchEl = document.getElementById('search');

  async function load(query) {
    const params = new URLSearchParams();
    if (query) params.set('search', query);
    params.set('limit', '100');
    try {
      const { data } = await Instox.api('/products?' + params.toString());
      if (!data.length) {
        listEl.innerHTML = '';
        emptyEl.style.display = query ? 'none' : 'block';
        if (query) listEl.innerHTML = '<p style="color:var(--muted);text-align:center;padding:20px">No products found.</p>';
        return;
      }
      emptyEl.style.display = 'none';
      listEl.innerHTML = data.map(renderItem).join('');
      bindRowActions();
    } catch (e) {
      Instox.toast(e.message, 'error');
    }
  }

  function stockClass(q) {
    if (q === 0) return 'stock-out';
    if (q <= 5) return 'stock-low';
    return '';
  }

  function renderItem(p) {
    return `
      <div class="product-item" data-id="${p.id}">
        ${Instox.thumbHtml(p.photo_url, p.name)}
        <div style="flex:1; min-width:0">
          <div class="unique-id">${Instox.escapeHtml(p.unique_id || '')}</div>
          <div class="name">${Instox.escapeHtml(p.name)}</div>
          <div class="meta">
            ${Instox.fmtMoney(p.retail_price)} retail · cost ${Instox.fmtMoney(p.cost_price)}
            ${p.category_name ? '· ' + Instox.escapeHtml(p.category_name) : ''}
          </div>
        </div>
        <div style="text-align:right">
          <div class="${stockClass(p.quantity)}">${p.quantity === 0 ? 'Out of stock' : p.quantity + ' in stock'}</div>
          <div style="margin-top:6px; display:flex; gap:6px; justify-content:flex-end">
            <a href="/product_form.html?id=${p.id}" class="btn btn-sm btn-secondary">Edit</a>
            <button class="btn btn-sm btn-danger" data-act="delete" data-id="${p.id}">Delete</button>
          </div>
        </div>
      </div>`;
  }

  function bindRowActions() {
    listEl.querySelectorAll('button[data-act="delete"]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        if (!confirm('Delete this product?')) return;
        try {
          await Instox.api('/products/' + id, { method: 'DELETE' });
          Instox.toast('Deleted', 'success');
          load(searchEl.value.trim());
        } catch (e) {
          Instox.toast(e.message, 'error');
        }
      });
    });
  }

  searchEl.addEventListener('input', Instox.debounce(() => load(searchEl.value.trim()), 200));
  load('');
})();
