# Instox — Implementation Plan & Architecture
## Complete Handoff Document

**Project:** Instox — Smart Billing & Inventory for Small Shops
**Author:** Nivedya M S
**Date:** June 2026
**Status:** Ready for Implementation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Architecture Overview](#4-architecture-overview)
5. [Tech Stack](#5-tech-stack)
6. [Database Schema](#6-database-schema)
7. [API Design](#7-api-design)
8. [Frontend Components](#8-frontend-components)
9. [File Structure](#9-file-structure)
10. [Implementation Phases](#10-implementation-phases)
11. [User Stories & Acceptance Criteria](#11-user-stories--acceptance-criteria)
12. [Business Rules](#12-business-rules)
13. [Security & Access Control](#13-security--access-control)
14. [Deployment](#14-deployment)
15. [Open Questions](#15-open-questions)

---

## 1. Project Overview

**Instox** is a mobile-first web application designed for small shop owners (textile, footwear, general stores) in India. The app solves five core problems:

1. **Manual price calculation** — shop owners spend hours calculating retail prices with 30% markup
2. **No profit visibility** — owners don't know if they're actually profitable
3. **Slow product search** — when customers ask "do you have X?", owners manually search shelves
4. **Purchase list management** — paper lists get forgotten, causing missed wholesale purchases
5. **No stock tracking** — owners don't know what's left, what's sold, what's old

**The product is NOT an ML/AI system.** It's a simple, practical tool that solves real problems for real shop owners. ML features (demand forecasting, dynamic pricing) are future enhancements only after the MVP is validated with real users.

---

## 2. Problem Statement

### Current State (How Shop Owners Work Today)

**New Stock Day Process (2-3 hours):**
1. Unload all products in one pile
2. Sit with family, physical bill, pen, calculator, price stickers
3. Match each product from pile with physical bill (verify quantities)
4. Calculate single item price from set price (e.g., set of 5 costs ₹500 → 1 item = ₹100)
5. Add 30% profit markup (SECRET — only family knows)
6. Write price on sticker → stick on product
7. Put products on shelves

**Billing Process:**
1. Customer brings items to counter
2. Owner writes items on paper with prices
3. Manually calculates total
4. Often makes errors in price or quantity

**Purchase List:**
1. Write list on paper at home
2. Carry paper to wholesale shop
3. If paper is forgotten → call family to check → waste time

**Profit/Loss:**
- Owners do NOT calculate profit per sale
- They "go with the flow" assuming they're profitable
- Many small businesses fail because they don't know their actual margins

### Desired State (With Instox)

**New Stock Day Process (20-30 minutes):**
1. Open app → Add products with wholesale price
2. App auto-calculates retail price (wholesale + 30%)
3. Print price labels OR show price on screen
4. Put products on shelves

**Billing Process:**
1. Search product by name (2 seconds)
2. Select items → App generates bill
3. Customer sees ONLY retail price (profit hidden)
4. Owner sees profit per sale automatically

**Purchase List:**
1. Add items to app → Saved to cloud
2. Access from any phone → Never forget

**Profit/Loss:**
1. Every sale shows: items, total, profit
2. Daily/monthly reports show actual business health

---

## 3. Target Users

### Primary User: Shop Owner

| Attribute | Description |
|-----------|-------------|
| **Who** | Family-run shop owner (textile, footwear, general store) |
| **Age** | 30-55 years |
| **Tech skills** | Basic smartphone, uses WhatsApp |
| **Revenue** | ₹5-25 lakh/year |
| **Employees** | 1-3 (often family members) |
| **Location** | Kerala, India (expandable to other states) |
| **Current tools** | Pen, paper, calculator, Excel (sometimes) |
| **Pain** | Wastes hours on manual calculations, doesn't know actual profit |
| **Goal** | Spend less time on math, more time growing business |

### Secondary User: Customer

| Attribute | Description |
|-----------|-------------|
| **Who** | Walk-in customer at the shop |
| **Interaction** | Receives bill only |
| **Needs** | Correct bill, clear pricing |
| **Should NOT see** | Cost price, profit margin, stock levels |

---

## 4. Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Mobile Browser (User's Phone)          │    │
│  │                                                     │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │           Frontend (HTML/CSS/JS)            │   │    │
│  │  │                                             │   │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │   │    │
│  │  │  │ Search  │ │ Billing │ │  Dashboard  │  │   │    │
│  │  │  │ Bar     │ │ Screen  │ │  (Owner)    │  │   │    │
│  │  │  └─────────┘ └─────────┘ └─────────────┘  │   │    │
│  │  │                                             │   │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │   │    │
│  │  │  │ Product │ │ Purchase│ │  Sales      │  │   │    │
│  │  │  │ List    │ │ List    │ │  History    │  │   │    │
│  │  │  └─────────┘ └─────────┘ └─────────────┘  │   │    │
│  │  └─────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ HTTP/REST API                    │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              SERVER LAYER (Flask)                    │    │
│  │                                                     │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │              Flask Application              │   │    │
│  │  │                                             │   │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │   │    │
│  │  │  │ Auth    │ │ Product │ │    Sale     │  │   │    │
│  │  │  │ Module  │ │ Module  │ │   Module    │  │   │    │
│  │  │  └─────────┘ └─────────┘ └─────────────┘  │   │    │
│  │  │                                             │   │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │   │    │
│  │  │  │ Search  │ │ Price   │ │  Report     │  │   │    │
│  │  │  │ Module  │ │ Calc    │ │  Module     │  │   │    │
│  │  │  └─────────┘ └─────────┘ └─────────────┘  │   │    │
│  │  └─────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ SQL                               │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DATA LAYER (SQLite/PostgreSQL)         │    │
│  │                                                     │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │    │
│  │  │ Users   │ │Products │ │  Sales  │ │  Sale   │  │    │
│  │  │ Table   │ │ Table   │ │  Table  │ │  Items  │  │    │
│  │  │         │ │         │ │         │ │  Table  │  │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │    │
│  │                                                     │    │
│  │  ┌─────────┐ ┌─────────┐                           │    │
│  │  │ Purchase│ │Categories│                          │    │
│  │  │ List    │ │  Table   │                          │    │
│  │  │ Table   │ │         │                           │    │
│  │  └─────────┘ └─────────┘                           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Customer asks "Do you have blue curtains?"
         │
         ▼
┌─────────────────────┐
│  Owner searches     │
│  "blue curtain"     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  API: GET /products │
│  ?search=blue       │
│  curtain            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Database query     │
│  SELECT * FROM      │
│  products WHERE     │
│  name LIKE '%blue   │
│  curtain%'          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Results displayed  │
│  "Blue Curtain 6x8" │
│  ₹260 | Stock: 12   │
│  Found in 0.5 sec   │
└─────────────────────┘
```

---

## 5. Tech Stack

### Backend

| Component | Technology | Reason |
|-----------|-----------|--------|
| **Language** | Python 3.10+ | Simple, widely used, good ecosystem |
| **Framework** | Flask 3.0 | Lightweight, easy to learn, fast to build |
| **Database** | SQLite (MVP) → PostgreSQL (Production) | SQLite for simplicity, PostgreSQL for scalability |
| **ORM** | SQLAlchemy | Database abstraction, easy migrations |
| **Authentication** | Flask-Login | Simple session-based auth |

### Frontend

| Component | Technology | Reason |
|-----------|-----------|--------|
| **Structure** | HTML5 | Simple, no build step required |
| **Styling** | CSS3 + Bootstrap 5 | Mobile-responsive out of the box |
| **Interactivity** | Vanilla JavaScript | No framework needed for MVP |
| **Charts** | Chart.js | Simple chart library for dashboards |
| **Icons** | Font Awesome | Professional icons |

### Why NOT React/Vue/Angular?

For MVP, vanilla HTML/CSS/JS is better because:
1. No build step (no npm, no webpack)
2. Faster to develop
3. Easier to maintain
4. Can always migrate to React later
5. Shop owners need simplicity, not SPA complexity

---

## 6. Database Schema

### Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│       users         │       │     categories      │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │       │ id (PK)             │
│ username            │       │ name                │
│ email               │       │ description         │
│ password_hash       │       │ created_at          │
│ shop_name           │       └──────────┬──────────┘
│ profit_percentage   │                  │
│ created_at          │                  │
└──────────┬──────────┘                  │
           │                             │
           │ 1                          │ 1
           │                            │
           │ *                          │ *
┌──────────┴──────────┐       ┌──────────┴──────────┐
│      products       │       │    purchase_lists   │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │       │ id (PK)             │
│ user_id (FK)        │       │ user_id (FK)        │
│ category_id (FK)    │       │ item_name           │
│ name                │       │ quantity            │
│ description         │       │ is_purchased        │
│ cost_price          │       │ created_at          │
│ retail_price        │       └─────────────────────┘
│ quantity            │
│ sku                 │
│ created_at          │
│ updated_at          │
└──────────┬──────────┘
           │
           │ 1
           │
           │ *
┌──────────┴──────────┐       ┌─────────────────────┐
│       sales         │       │     sale_items      │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │       │ id (PK)             │
│ user_id (FK)        │       │ sale_id (FK)        │
│ customer_name       │       │ product_id (FK)     │
│ total_amount        │       │ quantity            │
│ total_profit        │       │ unit_price          │
│ created_at          │       │ unit_cost           │
└─────────────────────┘       │ profit              │
                              └─────────────────────┘
```

### SQL Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    shop_name VARCHAR(100),
    profit_percentage DECIMAL(5,2) DEFAULT 30.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Products table
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    cost_price DECIMAL(10,2) NOT NULL,
    retail_price DECIMAL(10,2) NOT NULL,
    quantity INTEGER DEFAULT 0,
    sku VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Sales table
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    customer_name VARCHAR(100),
    total_amount DECIMAL(10,2) NOT NULL,
    total_profit DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Sale items table
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    profit DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Purchase list table
CREATE TABLE purchase_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 1,
    is_purchased BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_products_user_id ON products(user_id);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_sales_user_id ON sales(user_id);
CREATE INDEX idx_sales_created_at ON sales(created_at);
CREATE INDEX idx_sale_items_sale_id ON sale_items(sale_id);
CREATE INDEX idx_purchase_lists_user_id ON purchase_lists(user_id);
```

---

## 7. API Design

### Base URL: `http://localhost:5000/api`

### Authentication Endpoints

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/auth/register` | Register new user | `{username, email, password, shop_name}` |
| POST | `/auth/login` | Login user | `{email, password}` |
| POST | `/auth/logout` | Logout user | — |
| GET | `/auth/me` | Get current user | — |

### Product Endpoints

| Method | Endpoint | Description | Request Body/Params |
|--------|----------|-------------|---------------------|
| GET | `/products` | List all products | `?search=&category=&page=&limit=` |
| GET | `/products/:id` | Get single product | — |
| POST | `/products` | Create product | `{name, cost_price, quantity, category_id, description}` |
| PUT | `/products/:id` | Update product | `{name, cost_price, quantity, category_id}` |
| DELETE | `/products/:id` | Delete product | — |
| GET | `/products/search` | Search products | `?q=blue+curtain` |
| GET | `/products/low-stock` | Get low stock items | `?threshold=5` |

### Sales Endpoints

| Method | Endpoint | Description | Request Body/Params |
|--------|----------|-------------|---------------------|
| GET | `/sales` | List all sales | `?start_date=&end_date=&page=` |
| GET | `/sales/:id` | Get sale details | — |
| POST | `/sales` | Create new sale | `{customer_name, items: [{product_id, quantity}]}` |
| GET | `/sales/today` | Get today's sales | — |
| GET | `/sales/summary` | Get sales summary | `?period=daily\|weekly\|monthly` |

### Purchase List Endpoints

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| GET | `/purchase-list` | Get all items | — |
| POST | `/purchase-list` | Add item | `{item_name, quantity}` |
| PUT | `/purchase-list/:id` | Update item | `{is_purchased}` |
| DELETE | `/purchase-list/:id` | Delete item | — |

### Category Endpoints

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| GET | `/categories` | List all categories | — |
| POST | `/categories` | Create category | `{name, description}` |
| PUT | `/categories/:id` | Update category | `{name}` |
| DELETE | `/categories/:id` | Delete category | — |

### Dashboard Endpoints

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/dashboard` | Get dashboard data | `{today_sales, today_profit, monthly_sales, monthly_profit, stock_value, low_stock_count}` |
| GET | `/reports/profit` | Profit report | `{daily: [], weekly: [], monthly: []}` |
| GET | `/reports/stock` | Stock report | `{total_items, total_value, low_stock: []}` |

### API Response Format

**Success:**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "Blue Curtain 6x8",
        "cost_price": 200.00,
        "retail_price": 260.00,
        "quantity": 12
    }
}
```

**Error:**
```json
{
    "success": false,
    "error": "Product not found",
    "message": "No product with id 999 exists"
}
```

**Paginated:**
```json
{
    "success": true,
    "data": [...],
    "pagination": {
        "page": 1,
        "limit": 20,
        "total": 150,
        "pages": 8
    }
}
```

---

## 8. Frontend Components

### Pages

| Page | URL | Description | Access |
|------|-----|-------------|--------|
| **Login** | `/login` | User login form | Public |
| **Register** | `/register` | User registration form | Public |
| **Dashboard** | `/` | Main dashboard with stats | Owner only |
| **Products** | `/products` | Product list with search | Owner only |
| **Add Product** | `/products/new` | Add new product form | Owner only |
| **Edit Product** | `/products/:id/edit` | Edit product form | Owner only |
| **Billing** | `/billing` | Generate bills | Owner only |
| **Sales History** | `/sales` | View past sales | Owner only |
| **Purchase List** | `/purchase-list` | Manage purchase list | Owner only |
| **Reports** | `/reports` | Profit/loss reports | Owner only |

### Components

```
┌─────────────────────────────────────────────────┐
│                   Layout                        │
│  ┌───────────────────────────────────────────┐  │
│  │              Navbar                        │  │
│  │  [Logo] [Dashboard] [Products] [Billing]  │  │
│  │  [Sales] [Reports] [Profile] [Logout]     │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │              Content Area                  │  │
│  │                                           │  │
│  │  ┌─────────────┐  ┌─────────────────────┐│  │
│  │  │   Sidebar   │  │     Main Content    ││  │
│  │  │             │  │                     ││  │
│  │  │  - Search   │  │  - Product Grid     ││  │
│  │  │  - Filter   │  │  - Billing Form     ││  │
│  │  │  - Categories│ │  - Dashboard Cards  ││  │
│  │  │             │  │  - Charts           ││  │
│  │  └─────────────┘  └─────────────────────┘│  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │              Footer                        │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Key UI Elements

**1. Search Bar (Critical Feature)**
```
┌─────────────────────────────────────────┐
│ 🔍 Search products...                   │
└─────────────────────────────────────────┘
```
- Instant search (results appear as you type)
- Shows: Product name, price, stock count
- Click to add to bill

**2. Product Card**
```
┌─────────────────────────────────────┐
│ Blue Curtain 6x8                    │
│ ─────────────────────────────────── │
│ Retail: ₹260    Stock: 12          │
│ Category: Curtains                  │
│                                     │
│ [Edit]  [Delete]  [Add to Bill]    │
└─────────────────────────────────────┘
```

**3. Billing Screen**
```
┌─────────────────────────────────────┐
│ 🛒 BILLING                          │
│ ─────────────────────────────────── │
│ Customer: [________________]        │
│                                     │
│ Items:                              │
│ ┌───────────────────────────────┐   │
│ │ Blue Curtain 6x8    ×2  ₹520 │   │
│ │ White Sheet 4x6     ×1  ₹180 │   │
│ └───────────────────────────────┘   │
│                                     │
│ Search: [________________] 🔍      │
│                                     │
│ ─────────────────────────────────── │
│ TOTAL:                    ₹700     │
│                                     │
│ [Generate Bill]  [Clear]           │
└─────────────────────────────────────┘
```
**Note:** Owner sees profit in后台, customer sees ONLY this.

**4. Owner Dashboard**
```
┌─────────────────────────────────────┐
│ 📊 DASHBOARD                        │
│ ─────────────────────────────────── │
│                                     │
│ ┌──────────┐ ┌──────────┐          │
│ │ Today    │ │ Profit   │          │
│ │ ₹8,500   │ │ ₹2,100   │          │
│ │ Sales    │ │ Today    │          │
│ └──────────┘ └──────────┘          │
│                                     │
│ ┌──────────┐ ┌──────────┐          │
│ │ Items    │ │ Low      │          │
│ │ 147      │ │ Stock: 5 │          │
│ │ In Stock │ │ ⚠️ Alert │          │
│ └──────────┘ └──────────┘          │
│                                     │
│ [Sales Chart - Last 7 Days]        │
│ ▁▃▅▇▅▃▁                            │
└─────────────────────────────────────┘
```

---

## 9. File Structure

```
instox/
├── backend/
│   ├── app.py                 # Main Flask app
│   ├── config.py              # Configuration
│   ├── requirements.txt       # Python dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User model
│   │   ├── product.py        # Product model
│   │   ├── sale.py           # Sale model
│   │   └── purchase_list.py  # Purchase list model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication routes
│   │   ├── products.py       # Product routes
│   │   ├── sales.py          # Sales routes
│   │   ├── search.py         # Search routes
│   │   ├── purchase_list.py  # Purchase list routes
│   │   └── dashboard.py      # Dashboard routes
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── price_calculator.py  # Price calculation logic
│   │   └── auth.py              # Auth helpers
│   └── database/
│       ├── __init__.py
│       ├── db.py             # Database connection
│       └── schema.sql        # SQL schema
├── frontend/
│   ├── index.html            # Dashboard page
│   ├── login.html            # Login page
│   ├── register.html         # Register page
│   ├── products.html         # Product list
│   ├── product_form.html     # Add/edit product
│   ├── billing.html          # Billing page
│   ├── sales.html            # Sales history
│   ├── purchase_list.html    # Purchase list
│   ├── reports.html          # Reports page
│   ├── css/
│   │   ├── style.css         # Main styles
│   │   └── responsive.css    # Mobile styles
│   ├── js/
│   │   ├── app.js            # Main JavaScript
│   │   ├── search.js         # Search functionality
│   │   ├── billing.js        # Billing logic
│   │   ├── products.js       # Product management
│   │   └── dashboard.js      # Dashboard charts
│   └── assets/
│       ├── logo.png
│       └── favicon.ico
├── tests/
│   ├── test_products.py
│   ├── test_sales.py
│   └── test_auth.py
├── docs/
│   ├── PRD.md
│   ├── USER_STORIES.md
│   └── ARCHITECTURE.md      # This file
├── .gitignore
├── README.md
├── CHANGELOG.md
└── run.py                    # Entry point
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Days 1-2)

**Goal:** Setup project structure and database

**Tasks:**
- [ ] Initialize Flask app
- [ ] Setup SQLite database
- [ ] Create database schema (users, products, categories)
- [ ] Create User model with authentication
- [ ] Create Product model with CRUD
- [ ] Create basic API routes for products
- [ ] Setup requirements.txt

**Deliverable:** Backend API that can create/read/update/delete products

---

### Phase 2: Core Features (Days 3-5)

**Goal:** Implement MVP features

**Tasks:**
- [ ] Price calculator (auto-add profit %)
- [ ] Product search (by name)
- [ ] Create Sale model
- [ ] Create sale_items model
- [ ] Create billing API
- [ ] Profit tracking per sale
- [ ] Stock auto-decrement on sale

**Deliverable:** Complete backend with all MVP features

---

### Phase 3: Frontend (Days 6-8)

**Goal:** Build user interface

**Tasks:**
- [ ] Login/Register pages
- [ ] Dashboard page with stats
- [ ] Product list page with search
- [ ] Add/Edit product form
- [ ] Billing page
- [ ] Sales history page
- [ ] Mobile-responsive design

**Deliverable:** Working web app accessible via browser

---

### Phase 4: Polish (Days 9-10)

**Goal:** Test, fix bugs, deploy

**Tasks:**
- [ ] Test all features
- [ ] Fix bugs
- [ ] Add input validation
- [ ] Add error handling
- [ ] Deploy to Railway/Render
- [ ] Write README with setup instructions

**Deliverable:** Deployed app ready for users

---

### Phase 5: V2 Features (After MVP Validation)

**Goal:** Add should-have features

**Tasks:**
- [ ] Purchase list feature
- [ ] Low-stock alerts
- [ ] Daily/monthly profit reports
- [ ] Export bills as PDF
- [ ] Multiple user support

---

## 11. User Stories & Acceptance Criteria

### MVP Stories

**US-01: Product Catalog**
- As a shop owner, I want to add products with name, cost, and quantity
- Acceptance: Can add product with name, cost_price, quantity, category

**US-02: Auto Price Calculator**
- As a shop owner, I want to auto-calculate retail price from cost
- Acceptance: Enter cost → system adds 30% → shows retail price
- Acceptance: Profit % is configurable per user
- Acceptance: Customer NEVER sees cost or profit %

**US-03: Product Search**
- As a shop owner, I want to search products by name
- Acceptance: Type name → results appear in < 2 seconds
- Acceptance: Shows name, price, stock count

**US-04: Bill Generation**
- As a shop owner, I want to generate bills for customers
- Acceptance: Select items → calculate total → show retail price only
- Acceptance: Customer does not see cost or profit

**US-05: Profit Tracking**
- As a shop owner, I want to see profit on each sale
- Acceptance: After sale, shows: items, total, profit
- Acceptance: Only visible to owner

**US-06: Stock Tracking**
- As a shop owner, I want to track stock levels
- Acceptance: Stock auto-decreases when sale is made
- Acceptance: Shows current stock count per product

**US-07: Purchase List**
- As a shop owner, I want to save purchase lists on my phone
- Acceptance: Add items → saved to cloud → accessible anywhere

---

## 12. Business Rules

### Price Calculation

```
retail_price = cost_price × (1 + profit_percentage / 100)
```

**Example:**
- Cost price: ₹200
- Profit %: 30%
- Retail price: ₹200 × 1.30 = ₹260

### Profit Calculation

```
profit = retail_price - cost_price
```

**For a sale with multiple items:**
```
total_profit = sum(retail_price - cost_price) for each item
```

### Stock Management

```
When sale is made:
    product.quantity -= sale_item.quantity

When stock reaches 0:
    Mark as "Out of Stock"
    Show warning on dashboard
```

### Low Stock Threshold

```
Default threshold: 5 units
When product.quantity <= threshold:
    Show "Low Stock" warning
```

---

## 13. Security & Access Control

### User Roles

| Role | Can Do | Cannot Do |
|------|--------|-----------|
| **Owner** | Everything | — |
| **Customer** | View bill only | View cost, profit, stock, edit anything |

### Authentication

- Passwords stored as hashes (bcrypt)
- Session-based authentication
- Logout clears session

### Authorization

- Each user can only see their own products, sales, data
- No user can access another user's data
- API endpoints check `user_id` from session

### Data Validation

- All inputs validated on server side
- Cost price must be > 0
- Quantity must be >= 0
- Email must be valid format
- Password minimum 6 characters

---

## 14. Deployment

### Option 1: Railway (Recommended)

**Free tier available, easy deployment**

1. Create account at railway.app
2. Connect GitHub repo
3. Railway auto-detects Flask app
4. Add PostgreSQL database
5. Set environment variables:
   ```
   DATABASE_URL=postgresql://...
   SECRET_KEY=your-secret-key
   FLASK_ENV=production
   ```
6. Deploy

### Option 2: Render

**Free tier available**

1. Create account at render.com
2. New Web Service → Connect GitHub
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`
5. Add PostgreSQL database
6. Deploy

### Option 3: Local Development

```bash
cd /Users/nivedyams/instox
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

App runs at `http://localhost:5000`

---

## 15. Open Questions

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Profit %: fixed or per-item? | Fixed (30% for all) vs Per-item (different % per product) | **Start fixed**, add per-item in V2 |
| 2 | Single user or multi-user? | Single (owner only) vs Multi (family members) | **Start single**, add multi-user in V2 |
| 3 | Barcode scanning? | Yes vs No | **No for MVP**, add in V2 |
| 4 | Print receipts? | Yes vs No | **No for MVP**, show on screen only |
| 5 | Mobile app vs web app? | Native app vs Web app (accessed via phone browser) | **Web app** (access via browser, no install needed) |

---

## Appendix A: Dependencies

### requirements.txt

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-CORS==4.0.0
Werkzeug==3.0.1
python-dotenv==1.0.0
gunicorn==21.2.0
```

### Frontend CDN Links

```html
<!-- Bootstrap 5 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- Font Awesome -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
```

---

## Appendix B: Environment Variables

```bash
# .env file
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instox.db
```

---

## Appendix C: Git Commit Convention

Use this format for commit messages:

```
<type>: <description>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

Examples:
feat: add product catalog with CRUD operations
fix: price calculation rounding error
docs: update PRD with new requirements
```

---

**END OF IMPLEMENTATION PLAN**

This document is self-sufficient. Another agent can read it and start building the Instox MVP without any additional context.
