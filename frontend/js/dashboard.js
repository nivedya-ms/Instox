(async () => {
  const user = await Instox.bootstrapPage({ active: 'home' });
  if (!user) return;

  try {
    const { data } = await Instox.api('/dashboard');
    document.getElementById('today-sales').textContent = Instox.fmtMoney(data.today.total_amount);
    document.getElementById('today-count').textContent = `${data.today.sale_count} sale${data.today.sale_count === 1 ? '' : 's'}`;
    document.getElementById('today-profit').textContent = Instox.fmtMoney(data.today.total_profit);
    document.getElementById('month-sales').textContent = Instox.fmtMoney(data.month.total_amount);
    document.getElementById('month-profit-sub').textContent = `${Instox.fmtMoney(data.month.total_profit)} profit`;
    document.getElementById('low-stock-count').textContent = data.stock.low_stock_count;
    document.getElementById('stock-total').textContent = `${data.stock.total_products} products, ${data.stock.total_units} units`;

    renderAlerts(data.stock);

    const ctx = document.getElementById('sales-chart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.last_7_days.map((d) => d.date.slice(5)),
        datasets: [
          { label: 'Sales', data: data.last_7_days.map((d) => d.total_amount), backgroundColor: '#2563eb', borderRadius: 6 },
          { label: 'Profit', data: data.last_7_days.map((d) => d.total_profit), backgroundColor: '#16a34a', borderRadius: 6 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true } },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  } catch (e) {
    console.error(e);
    Instox.toast('Failed to load dashboard', 'error');
  }

  function renderAlerts(stock) {
    const widget = document.getElementById('low-stock-widget');
    const listEl = document.getElementById('alert-list');
    const titleEl = document.getElementById('alert-title');
    const subEl = document.getElementById('alert-sub');

    if (!stock.low_stock_count) {
      widget.style.display = 'none';
      return;
    }
    widget.style.display = 'block';
    widget.classList.toggle('has-out', stock.out_of_stock_count > 0);

    const parts = [];
    if (stock.out_of_stock_count) parts.push(`${stock.out_of_stock_count} out of stock`);
    if (stock.low_only_count) parts.push(`${stock.low_only_count} low`);
    titleEl.textContent = stock.out_of_stock_count > 0 ? '🚨 Stock alerts' : '⚠️ Low stock alerts';
    subEl.textContent = `${parts.join(' · ')} (threshold ≤ ${stock.threshold})`;

    listEl.innerHTML = stock.low_stock_items.slice(0, 8).map((p) => {
      const isOut = p.quantity <= 0;
      return `
        <div class="alert-row ${isOut ? 'out' : 'low'}">
          <div style="min-width:0;flex:1">
            <div class="name">${isOut ? '🔴' : '🟡'} ${Instox.escapeHtml(p.name)}</div>
            <div class="meta">${Instox.fmtMoney(p.retail_price)}${p.category_name ? ' · ' + Instox.escapeHtml(p.category_name) : ''}</div>
          </div>
          <span class="status-badge">${isOut ? 'Out of stock' : p.quantity + ' left'}</span>
        </div>`;
    }).join('');

    if (stock.low_stock_items.length > 8) {
      listEl.insertAdjacentHTML(
        'beforeend',
        `<div style="text-align:center;color:var(--muted);font-size:0.85rem;margin-top:6px">+ ${stock.low_stock_items.length - 8} more</div>`
      );
    }
  }
})();
