# V2 Implementation Plan
## Instox — All V2 Features

**Date:** June 2026
**Status:** Ready for Implementation

---

## Table of Contents

1. [V2 Feature Overview](#1-v2-feature-overview)
2. [Feature 1: Low-Stock Alerts](#2-feature-1-low-stock-alerts)
3. [Feature 2: Profit Reports](#3-feature-2-profit-reports)
4. [Feature 3: Sales History with Filters](#4-feature-3-sales-history-with-filters)
5. [Feature 4: PDF Bill Export](#5-feature-4-pdf-bill-export)
6. [Feature 5: Dashboard Charts](#6-feature-5-dashboard-charts)
7. [Database Changes](#7-database-changes)
8. [API Changes](#8-api-changes)
9. [Frontend Changes](#9-frontend-changes)
10. [Implementation Order](#10-implementation-order)
11. [Claude Code Prompts](#11-claude-code-prompts)

---

## 1. V2 Feature Overview

| # | Feature | Description | User Value |
|---|---------|-------------|------------|
| 1 | Low-stock alerts | Warn when stock ≤ threshold | Never run out of popular items |
| 2 | Profit reports | Daily/monthly/yearly profit views | Know if business is profitable |
| 3 | Sales history filters | Search sales by date, item, amount | Understand what's selling |
| 4 | PDF bill export | Download/share bills as PDF | Give customers receipts |
| 5 | Dashboard charts | Visual graphs of sales, profit, stock | See trends at a glance |

---

## 2. Feature 1: Low-Stock Alerts

### What It Does
Shows warnings when products are running low on stock.

### User Story
**As a** shop owner,
**I want to** be alerted when stock is running low,
**so that** I can restock before running out.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | Product stock ≤ 5 units | I view dashboard | Yellow "Low Stock" warning shown |
| 2 | Product stock = 0 | I view dashboard | Red "Out of Stock" warning shown |
| 3 | Multiple items low | Dashboard | All low-stock items listed together |
| 4 | I set custom threshold | Settings page | Threshold applies to all alerts |

### Database Changes

```sql
-- Add to users table
ALTER TABLE users ADD COLUMN low_stock_threshold INTEGER DEFAULT 5;
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/low-stock` | Get all low-stock products |
| PUT | `/api/settings/threshold` | Update low-stock threshold |

### Frontend Changes

**Dashboard Widget:**
```
┌─────────────────────────────────────┐
│ ⚠️ LOW STOCK ALERTS                 │
│ ─────────────────────────────────── │
│ 🔴 Chappal (Black) — 0 units       │
│ 🟡 Lining Material — 3 units       │
│ 🟡 Underwear (Pack) — 4 units      │
│                                     │
│ [View All Low Stock Items]          │
└─────────────────────────────────────┘
```

---

## 3. Feature 2: Profit Reports

### What It Does
Shows daily, weekly, and monthly profit summaries.

### User Story
**As a** shop owner,
**I want to** see profit reports for any time period,
**so that** I know if my business is actually making money.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I view daily report | Today | Shows: total sales, total profit, items sold |
| 2 | I view weekly report | This week | Shows: daily breakdown, weekly total |
| 3 | I view monthly report | This month | Shows: daily breakdown, monthly total |
| 4 | I compare months | Select two months | Shows comparison chart |
| 5 | I filter by category | Select category | Shows profit for that category only |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/profit?period=daily` | Daily profit report |
| GET | `/api/reports/profit?period=weekly` | Weekly profit report |
| GET | `/api/reports/profit?period=monthly` | Monthly profit report |
| GET | `/api/reports/profit?start=&end=` | Custom date range |
| GET | `/api/reports/profit?category_id=` | Filter by category |

### Frontend Changes

**Reports Page:**
```
┌─────────────────────────────────────┐
│ 📊 PROFIT REPORTS                   │
│ ─────────────────────────────────── │
│                                     │
│ Period: [Daily ▼] [Weekly] [Monthly]│
│ Category: [All Categories ▼]       │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ TODAY — June 29, 2026          │ │
│ │                                 │ │
│ │ Total Sales:    ₹8,500         │ │
│ │ Total Cost:     ₹6,400         │ │
│ │ Total Profit:   ₹2,100         │ │
│ │ Profit Margin:  24.7%          │ │
│ │ Items Sold:     23              │ │
│ │                                 │ │
│ │ Best Sale: ₹1,200 (3 items)    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Chart: Profit Last 7 Days]        │
│ ████████████░░░░░░░░                │
│ Mon Tue Wed Thu Fri Sat Sun        │
└─────────────────────────────────────┘
```

---

## 4. Feature 3: Sales History with Filters

### What It Does
Shows all past sales with ability to search and filter.

### User Story
**As a** shop owner,
**I want to** search and filter my sales history,
**so that** I can find specific transactions and understand trends.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I view sales history | Any time | Shows all sales with date, items, total, profit |
| 2 | I filter by date range | Select dates | Shows only sales in that range |
| 3 | I search by customer name | Type name | Shows matching sales |
| 4 | I sort by amount | Click "Amount" | Sorts sales by total amount |
| 5 | I sort by date | Click "Date" | Sorts sales by date |
| 6 | I tap a sale | Click sale | Shows full breakdown |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sales` | List all sales |
| GET | `/api/sales?start_date=&end_date=` | Filter by date |
| GET | `/api/sales?customer=` | Search by customer |
| GET | `/api/sales?sort=amount&order=desc` | Sort by amount |
| GET | `/api/sales/:id` | Get sale details |

### Frontend Changes

**Sales History Page:**
```
┌─────────────────────────────────────┐
│ 📜 SALES HISTORY                    │
│ ─────────────────────────────────── │
│                                     │
│ Search: [________________] 🔍      │
│ From: [____] To: [____] [Filter]   │
│ Sort: [Date ▼] [Amount] [Profit]   │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Jun 29, 2026 — ₹8,500 (₹2,100)│ │
│ │ Customer: Walk-in               │ │
│ │ Items: 3 — Chappal, Lining,    │ │
│ │        Underwear                │ │
│ │ [View Details]                  │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Jun 28, 2026 — ₹3,200 (₹780)  │ │
│ │ Customer: Priya                 │ │
│ │ Items: 2 — Saree, Blouse       │ │
│ │ [View Details]                  │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Showing 1-20 of 147 sales          │
│ [← Prev] [1] [2] [3] ... [8] [Next →]│
└─────────────────────────────────────┘
```

---

## 5. Feature 4: PDF Bill Export

### What It Does
Generates professional PDF bills that can be downloaded or shared.

### User Story
**As a** shop owner,
**I want to** generate PDF bills for customers,
**so that** I can give them a professional receipt.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | Sale is completed | I click "Download PDF" | PDF is generated with all details |
| 2 | Customer views bill | PDF shows | Only retail price visible (no cost/profit) |
| 3 | I want to share | I click "Share" | PDF is shareable via WhatsApp/email |
| 4 | PDF format | Any sale | Shows: shop name, date, items, total, thank you note |

### Implementation

Use a Python library to generate PDFs:
- **fpdf2** — simple, lightweight
- **reportlab** — more features, professional

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sales/:id/pdf` | Download PDF for a sale |
| GET | `/api/sales/:id/share` | Generate shareable link |

### PDF Template

```
┌─────────────────────────────────────┐
│                                     │
│          INSTOX                     │
│    Your Shop Name                   │
│    Phone: XXX-XXXXXXX              │
│                                     │
│ ═══════════════════════════════════ │
│                                     │
│  Bill #: 0047                       │
│  Date: June 29, 2026               │
│  Customer: Walk-in                  │
│                                     │
│ ─────────────────────────────────── │
│  Item              Qty    Price     │
│ ─────────────────────────────────── │
│  Chappal (pair)     1    ₹150      │
│  Lining Material    1     ₹40      │
│  Underwear          1     ₹50      │
│ ─────────────────────────────────── │
│  TOTAL                    ₹240     │
│ ═══════════════════════════════════ │
│                                     │
│  Thank you for shopping!           │
│  Visit us again!                   │
│                                     │
└─────────────────────────────────────┘
```

---

## 6. Feature 5: Dashboard Charts

### What It Does
Visual charts showing sales trends, profit trends, and stock distribution.

### User Story
**As a** shop owner,
**I want to** see visual charts of my business data,
**so that** I can quickly understand trends.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I view dashboard | Any time | Shows sales chart for last 7 days |
| 2 | I view dashboard | Any time | Shows profit chart for last 7 days |
| 3 | I view dashboard | Any time | Shows stock distribution by category |
| 4 | I hover over chart | Mouse hover | Shows exact values |
| 5 | I change time period | Click "30 days" | Chart updates |

### Charts to Implement

| Chart | Type | Shows |
|-------|------|-------|
| **Sales Trend** | Line chart | Daily sales for last 7/30 days |
| **Profit Trend** | Line chart | Daily profit for last 7/30 days |
| **Stock Distribution** | Pie chart | Products by category |
| **Top Selling Items** | Bar chart | Top 10 products by quantity sold |
| **Sales by Day** | Bar chart | Which days are busiest |

### Frontend Changes

**Dashboard with Charts:**
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
│ ┌─────────────────────────────────┐ │
│ │ SALES TREND (Last 7 Days)      │ │
│ │                                 │ │
│ │      ╭─────╮                    │ │
│ │   ╭──╯     ╰──╮   ╭──╮        │ │
│ │ ──╯            ╰──╯  ╰──      │ │
│ │ Mon Tue Wed Thu Fri Sat Sun    │ │
│ │                                 │ │
│ │ [7 Days] [30 Days] [90 Days]   │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ PROFIT TREND (Last 7 Days)     │ │
│ │                                 │ │
│ │                                 │ │
│ │      ████                       │ │
│ │   ████  ████      ████         │ │
│ │ ████      ████  ████  ████    │ │
│ │ Mon Tue Wed Thu Fri Sat Sun    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ STOCK BY CATEGORY              │ │
│ │                                 │ │
│ │    🟢 Curtains (45%)           │ │
│ │    🔵 Fabrics (30%)            │ │
│ │    🟡 Accessories (15%)        │ │
│ │    🔴 Other (10%)              │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## 7. Database Changes

### New Table: settings

```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    low_stock_threshold INTEGER DEFAULT 5,
    profit_percentage DECIMAL(5,2) DEFAULT 30.00,
    shop_name VARCHAR(100),
    shop_address TEXT,
    shop_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Modified Table: users

```sql
-- Remove these columns (move to settings table)
-- profit_percentage → move to settings
-- shop_name → move to settings
```

---

## 8. API Changes

### New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get user settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/reports/profit` | Profit reports |
| GET | `/api/reports/stock` | Stock reports |
| GET | `/api/sales/:id/pdf` | Download PDF bill |
| GET | `/api/dashboard/charts` | Chart data |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| GET | `/api/dashboard` | Add low-stock count, alerts |
| GET | `/api/products` | Add stock status (low/out) |

---

## 9. Frontend Changes

### New Files

| File | Purpose |
|------|---------|
| `frontend/js/charts.js` | Chart.js integration |
| `frontend/js/reports.js` | Reports page logic |
| `frontend/js/pdf.js` | PDF generation |
| `frontend/css/charts.css` | Chart styles |

### Modified Files

| File | Changes |
|------|---------|
| `frontend/index.html` | Add charts, low-stock alerts |
| `frontend/sales.html` | Add filters, search, pagination |
| `frontend/reports.html` | Complete redesign with charts |
| `frontend/billing.html` | Add PDF download button |

---

## 10. Implementation Order

### Week 1: Core V2 Features

| Day | Feature | Tasks |
|-----|---------|-------|
| Day 1 | Low-stock alerts | DB change, API, dashboard widget |
| Day 2 | Profit reports | API, reports page, date filters |
| Day 3 | Sales history filters | API, search, sort, pagination |

### Week 2: Advanced Features

| Day | Feature | Tasks |
|-----|---------|-------|
| Day 4 | PDF bills | PDF generation, template, download |
| Day 5 | Dashboard charts | Chart.js, 4 chart types |
| Day 6 | Polish & test | Bug fixes, responsive design |
| Day 7 | Deploy | Push to GitHub, deploy to Railway |

---

## 11. Claude Code Prompts

### Prompt 1: Low-Stock Alerts

```
Add low-stock alerts to the dashboard:

1. Update database: Add low_stock_threshold to users table (default 5)
2. Create API endpoint: GET /api/products/low-stock
   - Returns products where quantity <= user's threshold
   - Include stock status: "out_of_stock" (0), "low" (<=threshold), "normal"
3. Create API endpoint: PUT /api/settings/threshold
   - Update user's low_stock_threshold
4. Update dashboard: Add "Low Stock Alerts" widget
   - Show red warning for out-of-stock items
   - Show yellow warning for low-stock items
   - Show count of low-stock items
5. Add settings page: Allow user to change threshold

Acceptance criteria:
- Dashboard shows low-stock alerts on page load
- Alerts update in real-time when stock changes
- User can customize threshold in settings
```

### Prompt 2: Profit Reports

```
Build profit reports feature:

1. Create API endpoint: GET /api/reports/profit
   - Query params: period (daily/weekly/monthly), start_date, end_date, category_id
   - Returns: total_sales, total_cost, total_profit, profit_margin, items_sold
   - For weekly/monthly: include daily breakdown
2. Create reports page (frontend/reports.html)
   - Date range selector (daily/weekly/monthly/custom)
   - Category filter dropdown
   - Summary cards: Total Sales, Total Cost, Total Profit, Margin %
   - Table showing daily breakdown
   - Chart showing profit trend
3. Add navigation link to reports page

Acceptance criteria:
- Reports page loads with today's data by default
- User can switch between daily/weekly/monthly views
- User can filter by category
- Profit margin is calculated correctly
```

### Prompt 3: Sales History with Filters

```
Enhance sales history page with filters and search:

1. Update API: GET /api/sales
   - Add query params: start_date, end_date, customer, sort, order, page, limit
   - Return paginated results with total count
2. Update sales.html page:
   - Add search bar for customer name
   - Add date range picker (from/to)
   - Add sort buttons (date, amount, profit)
   - Add pagination (20 items per page)
   - Show sale summary on each card
3. Add sale detail modal:
   - Click "View Details" shows full breakdown
   - List all items with quantities and prices

Acceptance criteria:
- Search filters results in real-time
- Date filter works correctly
- Sorting works for date, amount, and profit
- Pagination shows correct page numbers
- Sale detail shows all items
```

### Prompt 4: PDF Bills

```
Add PDF bill generation:

1. Install fpdf2: Add to requirements.txt
2. Create PDF template (backend/utils/pdf_template.py)
   - Shop name, address, phone at top
   - Bill number, date, customer name
   - Table: item name, quantity, price
   - Total amount at bottom
   - Thank you note
3. Create API endpoint: GET /api/sales/:id/pdf
   - Generate PDF for the sale
   - Return as downloadable file
4. Update billing page:
   - Add "Download PDF" button after sale
   - Add "Share" button (opens share dialog)
5. Update sales history:
   - Add PDF download button on each sale card

Acceptance criteria:
- PDF downloads correctly with all sale details
- Customer name and date are included
- Only retail price visible (no cost/profit)
- PDF is properly formatted and professional
```

### Prompt 5: Dashboard Charts

```
Add charts to dashboard using Chart.js:

1. Create API endpoint: GET /api/dashboard/charts
   - Returns data for:
     - sales_trend: last 7/30 days of sales
     - profit_trend: last 7/30 days of profit
     - stock_by_category: product count per category
     - top_selling: top 10 products by quantity sold
2. Create frontend/js/charts.js:
   - Sales trend line chart
   - Profit trend bar chart
   - Stock distribution pie chart
   - Top selling items horizontal bar chart
3. Update dashboard (index.html):
   - Add chart containers below summary cards
   - Add time period selector (7/30/90 days)
   - Charts load on page load
4. Add chart interactivity:
   - Hover shows exact values
   - Click to filter/zoom

Acceptance criteria:
- All 4 charts render correctly
- Charts update when time period changes
- Hover tooltips show exact values
- Charts are responsive (work on mobile)
- Data loads in < 2 seconds
```

---

## 12. Testing Checklist

### Low-Stock Alerts
- [ ] Dashboard shows alerts when stock ≤ threshold
- [ ] Out-of-stock items show red warning
- [ ] Low-stock items show yellow warning
- [ ] Threshold can be updated in settings
- [ ] Alerts update when stock changes

### Profit Reports
- [ ] Daily report shows today's data
- [ ] Weekly report shows 7-day breakdown
- [ ] Monthly report shows 30-day breakdown
- [ ] Category filter works
- [ ] Profit margin calculated correctly

### Sales History
- [ ] All sales displayed
- [ ] Search by customer works
- [ ] Date filter works
- [ ] Sorting works
- [ ] Pagination works

### PDF Bills
- [ ] PDF downloads correctly
- [ ] All sale details included
- [ ] Only retail price visible
- [ ] PDF is properly formatted

### Dashboard Charts
- [ ] All 4 charts render
- [ ] Time period selector works
- [ ] Hover tooltips work
- [ ] Charts are responsive

---

**END OF V2 IMPLEMENTATION PLAN**
