# Instox

Smart billing and inventory for small shops. Mobile-first web app that lets a shop owner add stock, auto-price with markup, search products in seconds, generate bills (with profit hidden from customers), track stock, and keep a wholesale purchase list.

## Stack

- **Backend:** Flask 3 + SQLAlchemy + Flask-Login (session auth)
- **Frontend:** Vanilla HTML/CSS/JS, Chart.js for dashboards (no build step)
- **Database:** SQLite (MVP) — swap `DATABASE_URL` for PostgreSQL in production
- **Package manager:** [uv](https://github.com/astral-sh/uv)

## Quick start

```bash
# Install deps (creates .venv automatically)
uv sync

# Copy environment template
cp .env.example .env

# Run the app
uv run python run.py
```

Open <http://localhost:5000>. If port 5000 is taken (macOS AirPlay), run with `PORT=5050 uv run python run.py`.

Register an account, add a few products, then generate a bill.

## Running tests

```bash
uv run pytest
```

## Project layout

```
instox/
├── backend/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Config + TestConfig
│   ├── database/db.py       # SQLAlchemy instance
│   ├── models/              # User, Product, Category, Sale, SaleItem, PurchaseListItem
│   ├── routes/              # auth, products, sales, purchase_list, categories, dashboard
│   └── utils/price_calculator.py
├── frontend/                # Static HTML pages + vanilla JS
│   ├── index.html  login.html  register.html
│   ├── products.html  product_form.html
│   ├── billing.html  sales.html
│   ├── purchase_list.html  reports.html
│   ├── css/style.css
│   └── js/{app,dashboard,products,billing}.js
├── tests/                   # pytest suite
├── docs/                    # PRD, user stories, implementation plan
├── pyproject.toml           # uv-managed dependencies
└── run.py                   # entry point
```

## API surface

Base: `/api`

| Group | Endpoints |
|-------|-----------|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET/PUT /auth/me` |
| Products | `GET/POST /products`, `GET/PUT/DELETE /products/<id>`, `GET /products/search?q=`, `GET /products/low-stock`, `POST /products/calculate-price` |
| Categories | `GET/POST /categories`, `PUT/DELETE /categories/<id>` |
| Sales | `GET/POST /sales`, `GET /sales/<id>`, `GET /sales/<id>/bill` (customer view, no profit), `GET /sales/today`, `GET /sales/summary?period=` |
| Purchase list | `GET/POST /purchase-list`, `PUT/DELETE /purchase-list/<id>` |
| Dashboard | `GET /dashboard`, `GET /reports/profit`, `GET /reports/stock` |

All responses are `{ "success": true, "data": ... }` or `{ "success": false, "error": ... }`.

## Business rules

- `retail_price = cost_price × (1 + profit_percentage / 100)` — default 30%, configurable per user (`PUT /api/auth/me`).
- Per-row override is also supported on create/update.
- Profit on each sale = `(retail − cost) × quantity` per item, summed.
- Stock decrements atomically on sale; sales with insufficient stock are rejected.
- Customer-facing bill (`/api/sales/<id>/bill`) strips cost and profit fields.
- All data is scoped to the authenticated user — no cross-tenant access.

## Deployment

`gunicorn` is included. Start command:

```bash
uv run gunicorn run:app --bind 0.0.0.0:$PORT
```

Set `SECRET_KEY` and `DATABASE_URL` in your hosting environment. For PostgreSQL: `DATABASE_URL=postgresql+psycopg2://user:pass@host/db`.

## Status

- [x] PM documentation (PRD, user stories, implementation plan)
- [x] MVP backend (auth, products, sales, purchase list, dashboard, reports)
- [x] MVP frontend (mobile-first, all pages wired)
- [x] Test suite (23 tests, all passing)
- [ ] Deploy to Railway / Render
- [ ] User feedback

## License

Private — Nivedya M S
