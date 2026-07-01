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

    const lowEl = document.getElementById('low-stock-list');
    if (!data.stock.low_stock_items.length) {
      lowEl.innerHTML = '<p style="color:var(--muted);margin:8px 0">All stock levels healthy.</p>';
    } else {
      lowEl.innerHTML = data.stock.low_stock_items
        .map(
          (p) => `
          <div class="product-item">
            <div>
              <div class="name">${Instox.escapeHtml(p.name)}</div>
              <div class="meta">${Instox.fmtMoney(p.retail_price)}</div>
            </div>
            <div class="${p.quantity === 0 ? 'stock-out' : 'stock-low'}">${p.quantity === 0 ? 'Out of stock' : p.quantity + ' left'}</div>
          </div>`
        )
        .join('');
    }

    const ctx = document.getElementById('sales-chart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.last_7_days.map((d) => d.date.slice(5)),
        datasets: [
          {
            label: 'Sales',
            data: data.last_7_days.map((d) => d.total_amount),
            backgroundColor: '#2563eb',
            borderRadius: 6,
          },
          {
            label: 'Profit',
            data: data.last_7_days.map((d) => d.total_profit),
            backgroundColor: '#16a34a',
            borderRadius: 6,
          },
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
})();
