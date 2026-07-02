(async () => {
  const user = await Instox.bootstrapPage({ active: 'billing' });
  if (!user) return;

  const searchEl = document.getElementById('search');
  const resultsEl = document.getElementById('search-results');
  const cartEl = document.getElementById('cart');
  const emptyCartEl = document.getElementById('empty-cart');
  const totalsEl = document.getElementById('cart-totals');
  const totalAmountEl = document.getElementById('total-amount');
  const totalProfitEl = document.getElementById('total-profit');
  const generateBtn = document.getElementById('generate-btn');
  const customerEl = document.getElementById('customer-name');
  const billOutputEl = document.getElementById('bill-output');

  const cart = new Map();

  function renderCart() {
    if (cart.size === 0) {
      cartEl.innerHTML = '';
      emptyCartEl.style.display = 'block';
      totalsEl.style.display = 'none';
      return;
    }
    emptyCartEl.style.display = 'none';
    totalsEl.style.display = 'block';

    let total = 0;
    let profit = 0;
    cartEl.innerHTML = '';
    cart.forEach((item, id) => {
      const lineTotal = item.retail_price * item.qty;
      const lineProfit = (item.retail_price - item.cost_price) * item.qty;
      total += lineTotal;
      profit += lineProfit;
      const row = document.createElement('div');
      row.className = 'cart-item';
      row.innerHTML = `
        <div style="flex:1; min-width:0">
          <div class="name">${Instox.escapeHtml(item.name)}</div>
          <div class="meta">${Instox.fmtMoney(item.retail_price)} × ${item.qty} = ${Instox.fmtMoney(lineTotal)}</div>
        </div>
        <div class="qty-controls">
          <button data-act="dec">−</button>
          <input type="number" min="1" max="${item.stock}" value="${item.qty}" />
          <button data-act="inc">+</button>
          <button data-act="del" style="color:var(--danger);border-color:#fecaca">×</button>
        </div>`;
      const [decBtn, qtyInput, incBtn, delBtn] = row.querySelectorAll('button, input');
      decBtn.addEventListener('click', () => { if (item.qty > 1) { item.qty--; renderCart(); } });
      incBtn.addEventListener('click', () => { if (item.qty < item.stock) { item.qty++; renderCart(); } else { Instox.toast('No more in stock', 'error'); } });
      qtyInput.addEventListener('change', () => {
        const v = Math.max(1, Math.min(item.stock, parseInt(qtyInput.value || '1', 10)));
        item.qty = v;
        renderCart();
      });
      delBtn.addEventListener('click', () => { cart.delete(id); renderCart(); });
      cartEl.appendChild(row);
    });
    totalAmountEl.textContent = Instox.fmtMoney(total);
    totalProfitEl.textContent = Instox.fmtMoney(profit);
  }

  async function doSearch() {
    const q = searchEl.value.trim();
    if (!q) { resultsEl.innerHTML = ''; return; }
    try {
      const { data } = await Instox.api('/products/search?q=' + encodeURIComponent(q));
      if (!data.length) { resultsEl.innerHTML = '<p style="color:var(--muted);padding:8px">No matches.</p>'; return; }
      resultsEl.innerHTML = data.map((p) => `
        <div class="product-item" data-id="${p.id}">
          ${Instox.thumbHtml(p.photo_url, p.name)}
          <div style="flex:1; min-width:0">
            <div class="unique-id">${Instox.escapeHtml(p.unique_id || '')}</div>
            <div class="name">${Instox.escapeHtml(p.name)}</div>
            <div class="meta">${Instox.fmtMoney(p.retail_price)} · ${p.quantity === 0 ? '<span class=\"stock-out\">Out of stock</span>' : p.quantity + ' in stock'}</div>
          </div>
          <button class="btn btn-sm" ${p.quantity === 0 ? 'disabled' : ''}>Add</button>
        </div>
      `).join('');
      resultsEl.querySelectorAll('.product-item').forEach((row, i) => {
        const p = data[i];
        row.addEventListener('click', () => {
          if (p.quantity === 0) return;
          const existing = cart.get(p.id);
          if (existing) {
            if (existing.qty < p.quantity) existing.qty++;
            else Instox.toast('No more in stock', 'error');
          } else {
            cart.set(p.id, { id: p.id, name: p.name, retail_price: p.retail_price, cost_price: p.cost_price, qty: 1, stock: p.quantity });
          }
          searchEl.value = '';
          resultsEl.innerHTML = '';
          renderCart();
          searchEl.focus();
        });
      });
    } catch (e) {
      Instox.toast(e.message, 'error');
    }
  }

  searchEl.addEventListener('input', Instox.debounce(doSearch, 180));

  generateBtn.addEventListener('click', async () => {
    if (cart.size === 0) return;
    generateBtn.disabled = true;
    try {
      const items = Array.from(cart.values()).map((i) => ({ product_id: i.id, quantity: i.qty }));
      const { data } = await Instox.api('/sales', { method: 'POST', body: { customer_name: customerEl.value.trim(), items } });
      renderBill(data);
      cart.clear();
      renderCart();
      customerEl.value = '';
      Instox.toast('Sale recorded · stock updated', 'success');
    } catch (e) {
      Instox.toast(e.message, 'error');
    } finally {
      generateBtn.disabled = false;
    }
  });

  function renderBill(sale) {
    const shop = user.shop_name || 'Instox';
    const lines = sale.items.map((it) => `
      <div class="bill-line">
        <span>${Instox.escapeHtml(it.product_name)} × ${it.quantity}</span>
        <span>${Instox.fmtMoney(it.subtotal)}</span>
      </div>
    `).join('');
    billOutputEl.style.display = 'block';
    billOutputEl.innerHTML = `
      <div class="card" id="bill-card">
        <h2 style="text-align:center;margin-top:0">${Instox.escapeHtml(shop)}</h2>
        <div style="text-align:center;color:var(--muted);font-size:0.85rem">${Instox.fmtDateTime(sale.created_at)} · Bill #${sale.id}</div>
        ${sale.customer_name ? `<div style="text-align:center;margin-top:8px">Customer: ${Instox.escapeHtml(sale.customer_name)}</div>` : ''}
        <div style="margin-top:16px">${lines}</div>
        <div class="bill-total">
          <span>Total</span>
          <span>${Instox.fmtMoney(sale.total_amount)}</span>
        </div>
        <div class="bill-profit">
          <span>Your profit on this sale</span>
          <span>${Instox.fmtMoney(sale.total_profit)}</span>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button id="print-btn" class="btn btn-block btn-secondary">🖨️ Print</button>
          <button id="share-btn" class="btn btn-block btn-secondary">Share</button>
        </div>
      </div>`;
    document.getElementById('print-btn').addEventListener('click', () => window.print());
    document.getElementById('share-btn').addEventListener('click', async () => {
      const text = `${shop}\nBill #${sale.id}\n\n` + sale.items.map((it) => `${it.product_name} x${it.quantity}  ${Instox.fmtMoney(it.subtotal)}`).join('\n') + `\n\nTotal: ${Instox.fmtMoney(sale.total_amount)}`;
      if (navigator.share) {
        try { await navigator.share({ title: 'Bill', text }); } catch (_) {}
      } else {
        await navigator.clipboard.writeText(text);
        Instox.toast('Copied to clipboard', 'success');
      }
    });
    billOutputEl.scrollIntoView({ behavior: 'smooth' });
  }

  renderCart();
})();
