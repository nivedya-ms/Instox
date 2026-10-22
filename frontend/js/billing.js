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
  const itemCountEl = document.getElementById('item-count');
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
    let totalQty = 0;
    cartEl.innerHTML = '';
    cart.forEach((item, id) => {
      const lineTotal = item.retail_price * item.qty;
      const lineProfit = (item.retail_price - item.cost_price) * item.qty;
      total += lineTotal;
      profit += lineProfit;
      totalQty += item.qty;
      const row = document.createElement('div');
      row.className = 'cart-item';
      row.innerHTML = `
        <div style="flex:1; min-width:0">
          <div class="name">${Instox.escapeHtml(item.name)}</div>
          <div class="meta">${Instox.fmtMoney(item.retail_price)} × ${item.qty} ${Instox.escapeHtml(item.unit || 'pcs')} = ${Instox.fmtMoney(lineTotal)}</div>
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
    const distinct = cart.size;
    itemCountEl.textContent = distinct === totalQty
      ? `${totalQty}`
      : `${totalQty} (${distinct} product${distinct === 1 ? '' : 's'})`;
  }

  function renderResults(products, heading) {
    if (!products.length) {
      resultsEl.innerHTML = '<p style="color:var(--muted);padding:8px">No matches.</p>';
      return;
    }
    const head = heading
      ? `<div style="font-size:0.75rem;color:var(--muted);padding:4px 8px;text-transform:uppercase;letter-spacing:0.5px">${Instox.escapeHtml(heading)}</div>`
      : '';
    resultsEl.innerHTML = head + products.map((p) => {
      const unit = p.unit || 'pieces';
      const stockLabel = p.quantity === 0
        ? '<span class="stock-out">Out of stock</span>'
        : `${p.quantity} ${Instox.escapeHtml(unit)}`;
      return `
        <div class="product-item" data-id="${p.id}">
          ${Instox.thumbHtml(p.photo_url, p.name)}
          <div style="flex:1; min-width:0">
            <div class="unique-id">${Instox.escapeHtml(p.unique_id || '')}</div>
            <div class="name">${Instox.escapeHtml(p.name)}</div>
            <div class="meta">${Instox.fmtMoney(p.retail_price)} · ${stockLabel}${p.category_name ? ' · ' + Instox.escapeHtml(p.category_name) : ''}</div>
          </div>
          <button class="btn btn-sm" ${p.quantity === 0 ? 'disabled' : ''}>Add</button>
        </div>`;
    }).join('');
    resultsEl.querySelectorAll('.product-item').forEach((row, i) => {
      const p = products[i];
      row.addEventListener('click', () => {
        if (p.quantity === 0) return;
        const existing = cart.get(p.id);
        if (existing) {
          if (existing.qty < p.quantity) existing.qty++;
          else Instox.toast('No more in stock', 'error');
        } else {
          cart.set(p.id, { id: p.id, name: p.name, retail_price: p.retail_price, cost_price: p.cost_price, qty: 1, stock: p.quantity, unit: p.unit || 'pieces' });
        }
        searchEl.value = '';
        renderCart();
        loadSuggestions();  // refresh suggestions after adding
        searchEl.focus();
      });
    });
  }

  async function loadSuggestions() {
    try {
      const { data } = await Instox.api('/products?sort=recent&limit=5');
      const inStock = data.filter((p) => p.quantity > 0);
      if (inStock.length === 0) {
        resultsEl.innerHTML = '';
        return;
      }
      renderResults(inStock, 'Recent products');
    } catch (_) {
      resultsEl.innerHTML = '';
    }
  }

  async function doSearch() {
    const q = searchEl.value.trim();
    if (!q) { loadSuggestions(); return; }
    try {
      const { data } = await Instox.api('/products/search?q=' + encodeURIComponent(q));
      renderResults(data, '');
    } catch (e) {
      Instox.toast(e.message, 'error');
    }
  }

  searchEl.addEventListener('input', Instox.debounce(doSearch, 180));
  loadSuggestions();

  // -----------------------------------------------------------------
  // Snap items → cart
  // -----------------------------------------------------------------
  const snapInput = document.getElementById('snap-input');
  const snapReview = document.getElementById('snap-review');

  function addCandidateToCart(cand, quantity) {
    const stock = cand.quantity;
    const qty = Math.max(1, Math.min(stock, quantity || 1));
    const existing = cart.get(cand.product_id);
    if (existing) {
      existing.qty = Math.min(existing.qty + qty, stock);
    } else {
      cart.set(cand.product_id, {
        id: cand.product_id,
        name: cand.name,
        retail_price: cand.retail_price,
        cost_price: cand.retail_price,  // unknown from vision; profit hidden
        qty,
        stock,
        unit: cand.unit || 'pieces',
      });
    }
  }

  function renderProposal(prop, index) {
    const auto = prop.auto_pick && prop.candidates.length > 0;
    const top = prop.candidates[0];
    return `
      <div class="proposal-row ${auto ? 'auto' : 'ambig'}" data-idx="${index}">
        <div class="proposal-header">
          <div>
            <div class="proposal-desc">${auto ? '✅' : '❓'} ${Instox.escapeHtml(prop.description)}</div>
            <div class="proposal-meta">detected ${prop.quantity} · confidence ${(prop.confidence * 100).toFixed(0)}%</div>
          </div>
          <div class="proposal-qty-controls">
            <button data-act="dec">−</button>
            <input type="number" min="1" value="${prop.quantity}" data-role="qty" />
            <button data-act="inc">+</button>
          </div>
        </div>
        ${prop.candidates.length ? `
          <div class="proposal-candidates">
            ${prop.candidates.map((c, i) => `
              <label class="proposal-candidate ${auto && i === 0 ? 'selected' : (i === 0 && !auto ? 'selected' : '')}" data-cand="${i}">
                <input type="radio" name="prop-${index}" value="${i}" ${(auto && i === 0) || (!auto && i === 0) ? 'checked' : ''} />
                ${Instox.thumbHtml(c.photo_url, c.name)}
                <div style="flex:1;min-width:0">
                  <div class="unique-id">${Instox.escapeHtml(c.unique_id)}</div>
                  <div class="name">${Instox.escapeHtml(c.name)}</div>
                  <div class="proposal-meta">${Instox.fmtMoney(c.retail_price)} · ${c.quantity} ${Instox.escapeHtml(c.unit)} in stock · match ${(c.score * 100).toFixed(0)}%</div>
                </div>
              </label>`).join('')}
          </div>` : `
          <div class="proposal-meta" style="color:var(--danger);padding:8px">No catalog match found — search manually.</div>`}
        <div style="text-align:right">
          <button class="btn btn-sm btn-secondary" data-act="skip">Skip</button>
        </div>
      </div>`;
  }

  function renderSnapReview(result) {
    if (result.error && (!result.proposals || result.proposals.length === 0)) {
      snapReview.style.display = 'block';
      snapReview.innerHTML = `
        <div class="card">
          <div class="alert error">${Instox.escapeHtml(result.error)}</div>
          <button id="snap-close" class="btn btn-block btn-secondary">Close</button>
        </div>`;
      document.getElementById('snap-close').addEventListener('click', () => {
        snapReview.style.display = 'none';
        snapReview.innerHTML = '';
      });
      return;
    }

    if (!result.proposals || result.proposals.length === 0) {
      snapReview.style.display = 'block';
      snapReview.innerHTML = `
        <div class="card">
          <div class="alert warning">The AI didn't find any items in that photo. Try again with better lighting or search manually.</div>
          <button id="snap-close" class="btn btn-block btn-secondary">Close</button>
        </div>`;
      document.getElementById('snap-close').addEventListener('click', () => {
        snapReview.style.display = 'none';
        snapReview.innerHTML = '';
      });
      return;
    }

    let methodLabel = '';
    if (result.method === 'mobileclip' && result.mobileclip_stats) {
      const s = result.mobileclip_stats;
      const backfill = s.backfilled ? ` · embedded ${s.backfilled} new` : '';
      methodLabel = `Matched with MobileCLIP · ${s.candidates_scanned} products · ${s.query_ms} ms embed + ${s.compare_ms} ms rank · top ${(s.top_similarity * 100).toFixed(0)}%${backfill}`;
    } else if (result.method === 'phash' && result.phash_stats) {
      const s = result.phash_stats;
      methodLabel = `Matched locally (pHash) · ${s.candidates_scanned} products in ${s.total_ms} ms · top ${(s.top_similarity * 100).toFixed(0)}%`;
    } else if (result.method === 'llm-vision') {
      methodLabel = 'Matched with vision AI';
    } else if (result.used_stub) {
      methodLabel = 'Stub mode';
    }
    if (result.fallback_from) {
      methodLabel = `⚠ Fell back from ${result.fallback_from}: ${result.fallback_reason || ''} — ` + methodLabel;
    }
    if (result.mobileclip_status && result.mobileclip_status.loading) {
      methodLabel = `⏳ MobileCLIP still downloading (${Math.round(result.mobileclip_status.seconds_since_load_started)}s). Used pHash for now — try again in a minute. ` + methodLabel;
    }
    const methodBanner = methodLabel
      ? `<div style="font-size:0.75rem;color:var(--muted);margin-bottom:8px">🔎 ${Instox.escapeHtml(methodLabel)}</div>`
      : '';
    const previewImg = window.__lastCapturedPhotoUrl
      ? `<img src="${window.__lastCapturedPhotoUrl}" alt="Captured" style="width:100px;height:100px;object-fit:cover;border-radius:10px;border:1px solid var(--border);flex-shrink:0" />`
      : '';
    const autoCount = result.proposals.filter((p) => p.auto_pick && p.candidates.length).length;
    const totalCount = result.proposals.length;

    snapReview.style.display = 'block';
    snapReview.innerHTML = `
      <div class="card">
        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:8px">
          ${previewImg}
          <div style="flex:1;min-width:0">
            <h3 style="margin:0">📷 ${totalCount} match${totalCount === 1 ? '' : 'es'}${autoCount ? ' · ' + autoCount + ' auto-picked' : ''}</h3>
            ${methodBanner}
          </div>
        </div>
        <div id="proposals">${result.proposals.map(renderProposal).join('')}</div>
        <div class="row" style="margin-top:8px">
          <button id="snap-add-all" class="btn btn-block btn-success">Add selected to cart</button>
        </div>
        <div class="row" style="margin-top:8px">
          <label for="snap-single-input" class="btn btn-block btn-secondary" style="cursor:pointer">📷 Snap one more item</label>
          <input type="file" id="snap-single-input" accept="image/*" capture="environment" style="display:none" />
          <button id="snap-cancel" class="btn btn-block btn-secondary">Cancel</button>
        </div>
      </div>`;

    const skipped = new Set();

    snapReview.querySelectorAll('.proposal-row').forEach((row) => {
      const idx = Number(row.dataset.idx);
      const prop = result.proposals[idx];
      const qtyInput = row.querySelector('input[data-role="qty"]');
      row.querySelector('button[data-act="dec"]').addEventListener('click', () => {
        const v = Math.max(1, parseInt(qtyInput.value || '1', 10) - 1);
        qtyInput.value = v;
      });
      row.querySelector('button[data-act="inc"]').addEventListener('click', () => {
        const v = parseInt(qtyInput.value || '1', 10) + 1;
        qtyInput.value = v;
      });
      row.querySelector('button[data-act="skip"]').addEventListener('click', () => {
        skipped.add(idx);
        row.style.opacity = '0.4';
        row.querySelectorAll('input, button').forEach((el) => (el.disabled = true));
      });
      row.querySelectorAll('label.proposal-candidate').forEach((lbl) => {
        lbl.addEventListener('click', () => {
          row.querySelectorAll('label.proposal-candidate').forEach((l) => l.classList.remove('selected'));
          lbl.classList.add('selected');
        });
      });
    });

    document.getElementById('snap-add-all').addEventListener('click', () => {
      let added = 0;
      result.proposals.forEach((prop, idx) => {
        if (skipped.has(idx) || !prop.candidates.length) return;
        const row = snapReview.querySelector(`.proposal-row[data-idx="${idx}"]`);
        const qty = parseInt(row.querySelector('input[data-role="qty"]').value || '1', 10);
        const selectedRadio = row.querySelector('input[type="radio"]:checked');
        const candIdx = selectedRadio ? Number(selectedRadio.value) : 0;
        const cand = prop.candidates[candIdx];
        if (!cand) return;
        addCandidateToCart(cand, qty);
        added += qty;
      });
      renderCart();
      snapReview.style.display = 'none';
      snapReview.innerHTML = '';
      Instox.toast(`Added ${added} item${added === 1 ? '' : 's'} to cart`, 'success');
      loadSuggestions();
    });

    document.getElementById('snap-cancel').addEventListener('click', () => {
      snapReview.style.display = 'none';
      snapReview.innerHTML = '';
    });

    // Single-item fallback: appends more proposals to the same review panel.
    const singleInput = document.getElementById('snap-single-input');
    singleInput.addEventListener('change', () => {
      const f = singleInput.files && singleInput.files[0];
      if (f) sendPhoto(f, 'single', /* append */ true);
    });
  }

  async function sendPhoto(file, mode, append = false) {
    if (file.size > 8 * 1024 * 1024) {
      Instox.toast('Photo too large (max 8 MB)', 'error');
      return;
    }
    const form = new FormData();
    form.append('photo', file);
    form.append('mode', mode);

    // Preview what was captured so it's obvious the photo did arrive.
    const previewUrl = URL.createObjectURL(file);
    window.__lastCapturedPhotoUrl = previewUrl;
    if (!append) {
      snapReview.style.display = 'block';
      snapReview.innerHTML = `
        <div class="card">
          <div style="display:flex;gap:12px;align-items:flex-start">
            <img src="${previewUrl}" alt="Captured" style="width:120px;height:120px;object-fit:cover;border-radius:10px;border:1px solid var(--border);flex-shrink:0" />
            <div style="flex:1">
              <div style="color:var(--muted);padding:12px 0">🔍 Matching against your catalog...</div>
            </div>
          </div>
        </div>`;
    }

    let body;
    try {
      const res = await fetch('/api/ai/identify', { method: 'POST', body: form, credentials: 'include' });
      body = await res.json();
      if (!res.ok || !body.success) throw new Error((body && body.error) || `HTTP ${res.status}`);
    } catch (err) {
      Instox.toast('AI identify failed: ' + err.message, 'error');
      snapReview.style.display = 'none';
      snapReview.innerHTML = '';
      return;
    }

    if (append) {
      // Merge new proposals into the existing review panel
      const existing = window.__lastIdentify || { proposals: [] };
      existing.proposals = existing.proposals.concat(body.data.proposals || []);
      existing.used_stub = existing.used_stub || body.data.used_stub;
      window.__lastIdentify = existing;
      renderSnapReview(existing);
    } else {
      window.__lastIdentify = body.data;
      renderSnapReview(body.data);
    }
  }

  snapInput.addEventListener('change', () => {
    const f = snapInput.files && snapInput.files[0];
    if (!f) return;
    sendPhoto(f, 'multi');
    snapInput.value = '';  // allow re-selecting the same file
  });

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
    const totalItems = sale.items.reduce((s, it) => s + it.quantity, 0);
    const distinctItems = sale.items.length;
    const itemsLabel = distinctItems === totalItems
      ? `${totalItems} item${totalItems === 1 ? '' : 's'}`
      : `${totalItems} item${totalItems === 1 ? '' : 's'} · ${distinctItems} product${distinctItems === 1 ? '' : 's'}`;
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
        <div class="bill-total" style="font-size:0.9rem;color:var(--muted);border-bottom:none;padding-bottom:4px">
          <span>Items</span>
          <span>${itemsLabel}</span>
        </div>
        <div class="bill-total">
          <span>Total</span>
          <span>${Instox.fmtMoney(sale.total_amount)}</span>
        </div>
        <div class="bill-profit">
          <span>Your profit on this sale</span>
          <span>${Instox.fmtMoney(sale.total_profit)}</span>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
          <button id="print-btn" class="btn btn-secondary" style="flex:1">🖨️ Print</button>
          <button id="whatsapp-btn" class="btn btn-success" style="flex:1;background:#25d366">🟢 WhatsApp</button>
          <button id="share-btn" class="btn btn-secondary" style="flex:1">Share</button>
        </div>
        <div id="share-fallback" style="display:none;margin-top:8px">
          <textarea id="share-text" class="form-control" rows="6" readonly></textarea>
          <div style="font-size:0.75rem;color:var(--muted);margin-top:4px">Long-press to copy.</div>
        </div>
      </div>`;
    document.getElementById('print-btn').addEventListener('click', () => window.print());

    const buildText = () =>
      `${shop}\nBill #${sale.id} · ${Instox.fmtDateTime(sale.created_at)}\n` +
      (sale.customer_name ? `Customer: ${sale.customer_name}\n` : '') +
      '\n' +
      sale.items.map((it) => `${it.product_name} × ${it.quantity}  ${Instox.fmtMoney(it.subtotal)}`).join('\n') +
      `\n\nItems: ${itemsLabel}\nTotal: ${Instox.fmtMoney(sale.total_amount)}\n\nThank you for shopping!`;

    document.getElementById('whatsapp-btn').addEventListener('click', () => {
      const text = buildText();
      // wa.me works on desktop + mobile; opens WhatsApp with the message ready to send.
      window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank');
    });

    document.getElementById('share-btn').addEventListener('click', async () => {
      const text = buildText();
      // Web Share API is the best UX when available.
      if (navigator.share) {
        try {
          await navigator.share({ title: `Bill #${sale.id}`, text });
          return;
        } catch (err) {
          if (err && err.name === 'AbortError') return;  // user cancelled
          // fall through to clipboard fallback
        }
      }
      // Clipboard fallback — needs a secure context (HTTPS or localhost).
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(text);
          Instox.toast('Bill copied to clipboard', 'success');
          return;
        } catch (_) { /* fall through */ }
      }
      // Last resort: reveal a text area for manual copy.
      const fallback = document.getElementById('share-fallback');
      const ta = document.getElementById('share-text');
      ta.value = text;
      fallback.style.display = 'block';
      ta.focus();
      ta.select();
      Instox.toast('Copy the text below manually', 'error');
    });
    billOutputEl.scrollIntoView({ behavior: 'smooth' });
  }

  renderCart();
})();
