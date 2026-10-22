# Instox — Progress Report

**As of:** July 2026
**Status:** Working MVP + AI features · pre-production
**Tests:** 129 passing

---

## TL;DR

Instox is a mobile-first billing + inventory app for small textile / footwear shops
in Kerala. It started as a Flask + SQLite + vanilla-JS MVP and has grown into a
PWA-installable app with two AI features shipped: **"Ask about your shop"**
(natural-language questions → SQL over your data) and **"Snap items on counter"**
(photo → catalog match via MobileCLIP embeddings).

Everything runs locally out of the box. Real LLM support is one env variable away
(`LLM_PROVIDER=openai_compat` + `LLM_BASE_URL=...`).

---

## What's Working

### V1 — Core MVP
| Feature | Status | Notes |
|---|---|---|
| User auth (register / login / logout / session) | ✅ | Flask-Login, bcrypt-hashed passwords |
| Products CRUD | ✅ | Name, cost, retail, quantity, SKU, description, category |
| Auto price calculator | ✅ | `retail = cost × (1 + profit% / 100)`, per-user default profit % |
| Product search | ✅ | Matches name, SKU, INSTOX-ID, case-insensitive |
| Bill generation | ✅ | Cart → sale, stock decrements atomically |
| Profit per sale | ✅ | Owner sees profit; customer bill (`/sales/<id>/bill`) strips profit + cost |
| Stock tracking | ✅ | Auto-decrement on sale, insufficient-stock rejection |
| Purchase list | ✅ | Cloud-saved shopping list with check-off |
| Dashboard | ✅ | Today, month, low-stock, 7-day chart |
| Categories | ✅ | Per-user categories with unit (pieces / meters / pairs) and icon |
| Sales history | ✅ | Filter by day / week / month / all-time |

### V2 — Alerts + Settings
| Feature | Status | Notes |
|---|---|---|
| Low-stock alerts | ✅ | Categorized (out-of-stock vs low), user-configurable threshold |
| Settings page | ✅ | Threshold, default profit %, shop name |
| Dashboard widget | ✅ | Red/yellow color-coded alert card above chart |

### V3 — Rich Products
| Feature | Status | Notes |
|---|---|---|
| Photo capture | ✅ | Mobile camera via `<input capture="environment">`, 8 MB cap |
| Auto unique ID | ✅ | `INSTOX-00001` format, sequential, searchable |
| Default categories | ✅ | 8 seeded on registration (Curtains, Running Material, Footwear, ...) with correct units |
| Per-category unit | ✅ | Meters for fabrics, pairs for footwear, pieces default |
| Recent-products suggestions | ✅ | Billing shows top-5 recent when search is empty |
| WhatsApp share for bills | ✅ | Primary share, native Share fallback, clipboard fallback, textarea fallback |

### AI — Chat With Your Shop
| Piece | Status | Notes |
|---|---|---|
| Endpoint `/api/ai/chat` | ✅ | Two-hop pipeline: NL → SQL → rows → NL answer |
| Read-only SQL sandbox | ✅ | Per-user temp views, `PRAGMA query_only`, SELECT-only validator |
| Generic OpenAI-compatible client | ✅ | Any provider via `LLM_BASE_URL` + `LLM_MODEL` (DeepSeek, Qwen, Zhipu, OpenAI, ...) |
| Stub mode | ✅ | Pattern-matched answers for a handful of questions, no network |
| Chat UI | ✅ | `/chat.html` — question input, streaming feedback, hidden SQL by design |

### AI — Photo → Cart
| Piece | Status | Notes |
|---|---|---|
| Endpoint `/api/ai/identify` | ✅ | Multipart photo → ranked catalog matches |
| **MobileCLIP-S0** semantic matching | ✅ | 43 MB ONNX, ~40 ms per photo on CPU, L2-normalized 512-dim embeddings |
| pHash fallback | ✅ | Kicks in while MobileCLIP is still downloading, or when explicitly requested |
| Vision LLM path | ✅ | Used when `LLM_PROVIDER != stub` (Qwen-VL, GLM-4V, GPT-4o, ...) |
| Embedding cache | ✅ | `products.photo_embedding BLOB` — computed on photo upload, backfilled lazily on first identify |
| Auto-pick vs top-3 UI | ✅ | Auto-pick when similarity ≥ 0.85; ambiguous → top-3 radio choices |
| Snap-one-more (single-item fallback) | ✅ | Multi-photo default + camera-again button for missed items |
| Benchmark playground `/vision_test.html` | ✅ | Side-by-side pHash vs MobileCLIP on real catalog photos |

### PWA
- `/manifest.json` — installable, standalone display, shortcuts to Bill / Ask / Add product
- `/sw.js` — cache-first app shell, network-only for API + uploads
- Icons at 192 and 512 px
- Add-to-home-screen works on Chrome/Safari — installs like a native app

---

## Architecture Snapshot

```
┌─────────────────────────────────────────────────────────────┐
│                    Mobile Browser (PWA)                     │
│  vanilla JS + HTML + Chart.js + ONNX-free pHash-in-JS       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / JSON (session cookie)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask 3 App (backend/)                   │
│                                                             │
│  Routes:                                                    │
│    /api/auth · /api/products · /api/sales · /api/categories │
│    /api/purchase-list · /api/dashboard · /api/settings      │
│    /api/ai/chat · /api/ai/identify · /api/ai/vision-*       │
│                                                             │
│  Services:                                                  │
│    services/llm.py           — OpenAI-compat client + stub  │
│    services/nl_to_sql.py     — NL → SQL → NL answer         │
│    services/sql_sandbox.py   — safe read-only SQL exec      │
│    services/photo_match.py   — vision-LLM identify pipeline │
│    services/vision_local.py  — pHash (pure Python)          │
│    services/mobileclip.py    — MobileCLIP-S0 ONNX inference │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  SQLite (instox.db)                         │
│                                                             │
│   users · categories · products (+embedding BLOB)           │
│   sales · sale_items · purchase_lists                       │
└─────────────────────────────────────────────────────────────┘

External:                                        Local cache:
  HuggingFace Hub (MobileCLIP weights)             ~/.cache/huggingface/
  LLM provider (optional, when configured)         backend/uploads/ (product photos)
```

---

## Tech Stack

| Layer | Tech | Why |
|---|---|---|
| Package mgr | uv | Fast, lockfile-based, one-command setup |
| Backend | Flask 3 + SQLAlchemy 2 | Small, well-known, zero magic |
| Auth | Flask-Login (session) | Simplest thing that works for single-shop use |
| DB | SQLite | File-backed, migrates via lightweight ALTER TABLE on startup, `DATABASE_URL` swaps to Postgres |
| ML runtime | ONNX Runtime | Ships without torch (~1 GB saved); MobileCLIP inference in ~40 ms on CPU |
| Vision model | MobileCLIP-S0 (`Xenova/mobileclip_s0`) | 43 MB fp32 vision encoder, semantic embeddings that survive angle/lighting changes |
| Text LLM | OpenAI-compatible client | Any provider works — DeepSeek default, Qwen/Zhipu/OpenAI via env |
| Frontend | Vanilla HTML/CSS/JS + Chart.js | No build step, 40 KB total, works on any browser |
| PWA | manifest.json + service worker | Installable, cached app shell, offline-friendly reads |

---

## Key Design Decisions

**Why SQLite, not Postgres.** One shop = one database. SQLite handles concurrent
reads fine for a single-owner app, and the file-based deploy story is dramatically
simpler. `DATABASE_URL` swap-in for Postgres later if we need multi-shop.

**Why vanilla JS, not React.** The whole frontend is ~40 KB. No build step means
you can edit a file and refresh. React would add ~130 KB and a build pipeline for
zero user-visible benefit at this scope.

**Why MobileCLIP-S0 over CLIP-ViT-B/32.** MobileCLIP is 43 MB vs CLIP's 335 MB, and
runs 3× faster on CPU. On real product photos the accuracy gap is minimal — the
distinguishing failure mode is "similar-looking products" which no CNN can fix
without more context.

**Why pHash as a fallback, not primary.** pHash was tried first (see commit history)
and lost. It only matches near-identical images — the moment you take a counter
photo at a different angle from the catalog photo, similarity drops below 60%
and the ranking becomes noise. Kept as a fallback because it works instantly
while MobileCLIP is still downloading.

**Why hide the SQL from the user in Ask.** Shop owner doesn't read SQL. Showing
it invites doubt in the answer. If verification is needed, we surface the source
rows below the answer instead.

**Why default LLM provider = stub.** Zero-config first-run: `uv sync && uv run
python run.py` gives you a working app immediately. Real LLM is one env variable
away when you want it.

**Why generic OpenAI-compatible client, not provider-specific.** DeepSeek, Qwen,
Zhipu, OpenAI, local vLLM — all speak the OpenAI API dialect. One client, all
endpoints, no lock-in.

---

## Directory Layout

```
instox/
├── backend/
│   ├── __init__.py           # app factory, migrations, warmup
│   ├── config.py             # Config + TestConfig
│   ├── database/db.py
│   ├── models/               # user, category, product, sale, purchase_list
│   ├── routes/               # auth, products, sales, purchase_list,
│   │                         # categories, dashboard, settings, ai
│   ├── services/             # llm, nl_to_sql, sql_sandbox,
│   │                         # photo_match, vision_local, mobileclip
│   ├── utils/price_calculator.py
│   └── uploads/              # product photos (git-ignored)
├── frontend/
│   ├── index.html            # dashboard
│   ├── login.html · register.html
│   ├── products.html · product_form.html
│   ├── billing.html          # + snap-items panel
│   ├── sales.html
│   ├── purchase_list.html
│   ├── settings.html
│   ├── chat.html             # AI chat
│   ├── vision_test.html      # AI vision benchmark playground
│   ├── manifest.json · sw.js
│   ├── css/style.css
│   ├── js/{app,dashboard,products,billing,phash}.js
│   └── icons/
├── tests/                    # 129 pytest tests
├── docs/
│   ├── PRD.md
│   ├── USER_STORIES.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── V2_IMPLEMENTATION_PLAN.md
│   ├── V3_IMPLEMENTATION_PLAN.md
│   └── PROGRESS.md           # this file
├── pyproject.toml            # uv-managed deps
├── uv.lock
├── run.py                    # entry point
└── .env.example
```

---

## Running It

```bash
uv sync                          # install deps
cp .env.example .env             # copy env template
PORT=5050 uv run python run.py   # start on http://localhost:5050

# Or the default port 5000 (may conflict with macOS AirPlay):
uv run python run.py

# Tests
uv run pytest -q
```

**First run:** MobileCLIP model (~43 MB) auto-downloads on server startup in a
background thread. Cached to `~/.cache/huggingface/hub` for all future runs.

**LAN access:** app binds to `0.0.0.0`, so any device on your Wi-Fi can hit
`http://<your-local-ip>:5050`. Note: mobile camera + clipboard APIs require
HTTPS on non-localhost origins — for real phone testing, tunnel with ngrok or
generate a mkcert dev cert.

---

## API Surface

**Base:** `/api`

| Group | Endpoints |
|---|---|
| **Auth** | `POST /auth/register · POST /auth/login · POST /auth/logout · GET/PUT /auth/me` |
| **Products** | `GET/POST /products · GET/PUT/DELETE /products/<id>` <br> `GET /products/search?q= · GET /products/low-stock` <br> `POST /products/calculate-price` <br> `POST/DELETE /products/<id>/photo` |
| **Categories** | `GET/POST /categories · PUT/DELETE /categories/<id>` |
| **Sales** | `GET/POST /sales · GET /sales/<id>` <br> `GET /sales/<id>/bill` (customer view, no profit) <br> `GET /sales/today · GET /sales/summary?period=` |
| **Purchase list** | `GET/POST /purchase-list · PUT/DELETE /purchase-list/<id>` |
| **Dashboard** | `GET /dashboard · GET /reports/profit · GET /reports/stock` |
| **Settings** | `GET/PUT /settings · PUT /settings/threshold` |
| **AI** | `GET /ai/status` <br> `POST /ai/chat` — NL question → answer <br> `POST /ai/identify` — photo → cart matches (mobileclip / phash / llm-vision) <br> `GET /ai/vision-benchmark/info` — catalog + method availability <br> `POST /ai/vision-benchmark` — side-by-side ranking |

**Response shape:** `{ "success": true, "data": ... }` or `{ "success": false, "error": ... }`.

---

## Configuration (`.env`)

```bash
# Core
FLASK_ENV=development
SECRET_KEY=change-me-to-a-long-random-string
DATABASE_URL=sqlite:///instox.db
PORT=5050

# LLM (OpenAI-compatible endpoint)
LLM_PROVIDER=stub                  # stub | openai_compat
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# Vision (defaults to LLM_* if unset)
VISION_API_KEY=
VISION_BASE_URL=
VISION_MODEL=qwen-vl-plus

# Disable MobileCLIP warmup on startup (useful for CI)
DISABLE_MOBILECLIP_WARMUP=
```

---

## What's Next (open threads)

**Ordered by rough priority — call the shots on what matters.**

1. **Real-world MobileCLIP accuracy on Nakshatra products.** We've validated the
   pipeline works. The open question: does semantic similarity actually rank the
   *right* curtain first when the counter photo is at a real angle in real
   lighting? Needs field testing.

2. **Suppliers.** Planned in `V3_IMPLEMENTATION_PLAN.md`, not yet built. Small
   scope: CRUD + FK on product + supplier view.

3. **Multi-user (family members).** Planned in V3, not built. Owner-adds-user
   flow, roles (owner vs family), permission gates on cost/profit fields.

4. **Category browsing page.** Planned in V3, not built. Grid of category cards
   with product counts.

5. **PDF bills.** Planned in V2, not built. `fpdf2` template with shop header,
   items, total, thank-you note.

6. **HTTPS for phone testing.** Right now the camera/share/clipboard APIs
   require HTTPS or localhost. mkcert-based dev cert or Cloudflare Tunnel setup.

7. **Voice → bill in Malayalam.** The killer feature if we go multi-modal AI.
   Whisper for transcription, then reuse the vision LLM pipeline for item
   extraction. Punts to a real device test.

8. **React Native rewrite.** Deferred — the PWA is doing everything a phone
   needs. Only worth doing if the app-store distribution channel matters.

---

## What's Not Being Built (and Why)

- **Multi-shop / multi-tenant.** One shop, one owner. If we ever expand, it's a
  clean fork with a `tenant_id` column, not a bolt-on now.
- **Barcode scanning.** Small shops don't have barcodes. Skipped in favor of
  photo-to-cart.
- **Full ERPNext-parity accounting.** ERPNext already exists. Instox is the
  "you actually use it" layer, not the "every accountant-approved feature" layer.
- **Payments integration.** Cash-only shops for MVP. UPI QR + Razorpay in a
  future turn when we have paying users asking for it.

---

## Test Coverage

| Suite | Tests | Focus |
|---|---|---|
| `test_auth.py` | 7 | Register / login / session / duplicate email |
| `test_products.py` | 8 | CRUD, search, low-stock, cross-user isolation |
| `test_sales.py` | 6 | Sale flow, stock decrement, insufficient stock, customer bill hides profit |
| `test_purchase_list.py` | 2 | CRUD basics |
| `test_low_stock.py` | 11 | Threshold, dashboard alerts, migration |
| `test_photo_and_unique_id.py` | 13 | Upload, sequential IDs, cross-user, old-DB migration |
| `test_v3_fixes.py` | 11 | Default categories, sort=recent, PWA endpoints, category units |
| `test_sql_sandbox.py` | 11 | SELECT-only validator, cross-tenant scoping, write-block |
| `test_ai_chat.py` | 5 | End-to-end NL → SQL → answer via stub |
| `test_photo_match.py` | 16 | Vision-LLM pipeline (with stub), catalog matcher scoring |
| `test_vision_local.py` | 11 | pHash correctness, ranking, endpoint contract |
| `test_mobileclip.py` | 10 | Embed / rank / cache / endpoint routing (skips if model unavailable) |
| **Total** | **129 passing** | ~10 s to run the full suite |
