# User Stories — Instox

## How to Read This Document

Each user story follows the format:
> **As a** [user], **I want to** [action], **so that** [benefit]

Acceptance criteria use Given/When/Then format.

---

## MVP Stories (Priority: Must Have)

### US-01: Add Products

**As a** shop owner,
**I want to** add products with name, cost, and quantity,
**so that** I can build my inventory digitally.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I enter product name "Blue Curtain 6x8" | I click "Add" | Product is saved with name |
| 2 | I enter cost price ₹200 | I click "Add" | Product shows cost ₹200 |
| 3 | I enter quantity 10 | I click "Add" | Product shows 10 in stock |
| 4 | I enter category "Curtains" | I click "Add" | Product is tagged with category |
| 5 | I leave name empty | I click "Add" | Error: "Name is required" |

---

### US-02: Auto Price Calculator

**As a** shop owner,
**I want to** enter the wholesale price and have the system auto-calculate retail price,
**so that** I don't waste time doing math manually.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I enter cost ₹100 | I click "Calculate" | Retail price shows ₹130 (30% markup) |
| 2 | I enter cost ₹500 for a set of 5 | I click "Calculate" | Shows: single cost ₹100, retail ₹130 |
| 3 | I change markup % to 25% | I click "Calculate" | Retail price updates to ₹125 |
| 4 | Customer views the bill | Any time | Customer sees ONLY retail price, NEVER cost or profit % |

---

### US-03: Search Products

**As a** shop owner,
**I want to** search for any product by name,
**so that** when a customer asks "do you have X?" I can answer in 2 seconds.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I type "blue curtain" | I press Enter or results auto-show | All blue curtain items appear |
| 2 | I type "6x8" | Results show | Items matching size appear |
| 3 | Item is out of stock | I search for it | Shows "Out of Stock" |
| 4 | No results found | Search complete | Shows "No products found" |
| 5 | Search results show | Display | Each result shows: name, price, stock count |

---

### US-04: Generate Bill

**As a** shop owner,
**I want to** select items and generate a bill for the customer,
**so that** billing is fast and accurate.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I select items for a sale | I click "Generate Bill" | Bill shows: item names, quantities, retail prices, total |
| 2 | Customer buys 3 items | Bill is generated | Total = sum of all 3 retail prices |
| 3 | Customer views the bill | Any time | NO cost price, NO profit % visible |
| 4 | I complete the sale | Sale is recorded | Stock decreases by sold quantities |
| 5 | I want to print/share bill | I click "Print" or "Share" | Bill is printable or shareable |

---

### US-05: Profit Per Sale

**As a** shop owner,
**I want to** see how much profit I made on each sale,
**so that** I know if my business is actually making money.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | Sale is completed with 3 items | I view sale details | Shows: items, total, profit |
| 2 | Profit = sum of (retail - cost) for each item | Calculation | Profit is accurate |
| 3 | Customer views bill | Any time | Customer does NOT see profit |
| 4 | I view today's sales | End of day | Shows: total sales, total profit |

---

### US-06: Stock Tracking

**As a** shop owner,
**I want to** track my stock levels automatically,
**so that** I know what's in stock and what's running low.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I add 10 units of a product | Product created | Stock shows 10 |
| 2 | I sell 3 units | Sale completed | Stock shows 7 |
| 3 | Stock reaches 0 | I check product | Shows "Out of Stock" |
| 4 | I view all products | Dashboard | Each shows current stock count |

---

### US-07: Purchase List

**As a** shop owner,
**I want to** save my wholesale purchase list on my phone,
**so that** I never forget what to buy even if I forget my paper list.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I add items to purchase list | I save | List is saved to cloud |
| 2 | I'm at wholesale shop | I open app on phone | List is accessible |
| 3 | I check off an item | I tap checkbox | Item is marked as purchased |
| 4 | I delete an item | I swipe/tap delete | Item is removed from list |

---

## V2 Stories (Priority: Should Have)

### US-08: Sales History

**As a** shop owner,
**I want to** see a history of all past sales,
**so that** I know what's selling and what's not.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I have past sales | I view sales history | Shows list of all sales with date, items, total, profit |
| 2 | I filter by date range | I select "This week" | Shows only this week's sales |
| 3 | I tap a sale | I view details | Shows full breakdown of that sale |

---

### US-09: Low Stock Alerts

**As a** shop owner,
**I want to** be alerted when stock is running low,
**so that** I can restock before running out.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | Product stock drops below 5 | I view dashboard | Yellow warning shown |
| 2 | Product stock reaches 0 | I view dashboard | Red "Out of Stock" shown |
| 3 | Multiple items low | Dashboard | All low-stock items listed together |

---

### US-10: Profit Dashboard

**As a** shop owner,
**I want to** see daily and monthly profit summaries,
**so that** I understand my business health at a glance.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I open dashboard | Any time | Shows today's sales and profit |
| 2 | I switch to monthly view | I tap "This Month" | Shows monthly totals |
| 3 | I compare months | I select different months | Shows comparison |

---

## V3 Stories (Priority: Could Have)

### US-11: Old Stock Alerts

**As a** shop owner,
**I want to** know which items have been sitting unsold for too long,
**so that** I can clear them before they become dead stock.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | Item unsold for > 60 days | I view dashboard | Orange warning "Old Stock" |
| 2 | Item unsold for > 90 days | I view dashboard | Red warning "Clearance Recommended" |

---

### US-12: Price Label Printing

**As a** shop owner,
**I want to** print price labels for new stock,
**so that** I don't have to write prices by hand.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I select products | I click "Print Labels" | Labels are generated with item name and retail price |
| 2 | Labels are printed | On paper | Each label shows: name, price (no cost visible) |

---

### US-13: Demand Forecasting

**As a** shop owner,
**I want to** know which items are likely to sell more next month,
**so that** I can stock up on popular items and avoid overstocking slow ones.

**Acceptance Criteria:**
| # | Given | When | Then |
|---|-------|------|------|
| 1 | I have 3 months of sales data | I view forecast | System suggests: "Stock more of X, less of Y" |
| 2 | Season is approaching (e.g., Onam) | System detects | Shows: "Expect 2x demand for traditional wear" |
