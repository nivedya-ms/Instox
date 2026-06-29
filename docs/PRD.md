# Product Requirements Document (PRD)
## Instox — Smart Billing & Inventory for Small Shops

**Version:** 1.0
**Author:** Nivedya M S
**Date:** June 2026
**Status:** Draft

---

## 1. Product Overview

### What is Instox?
Instox is a mobile-first web app that helps small shop owners:
- Generate bills automatically (with profit hidden from customers)
- Track inventory in real-time
- See profit on every sale
- Search products in 2 seconds
- Save purchase lists so they never forget what to buy

### Who is it for?
**Primary User:** Small shop owner (family-run business, 1-3 employees)
**Example:** A textile/footwear/general store in Kerala doing ₹5-25 lakh/year

### What problem does it solve?
| Problem | Current State | With Instox |
|---------|---------------|-------------|
| Price calculation | Manual math with calculator on new stock days | Enter cost → auto-calculates retail price |
| Profit visibility | "We just go with the flow" | See profit on every sale, daily/monthly reports |
| Customer asks "do you have X?" | Walk to shelf, search manually | Search in 2 seconds |
| Purchase lists | Paper lists, forget them = disaster | Saved on phone, always accessible |
| Billing errors | Manual bills, wrong prices | Auto-generated, accurate bills |

---

## 2. Goals & Success Metrics

### Business Goals
| Goal | Metric | Target |
|------|--------|--------|
| Reduce time on new stock processing | Hours per stock day | From 3 hours → 30 minutes |
| Give profit visibility | % of sales where owner knows profit | From 0% → 100% |
| Speed up product search | Time to answer "do you have X?" | From 2 minutes → 5 seconds |
| Reduce billing errors | Error rate | From ~5% → <1% |

### Product Goals
| Goal | Metric | Target |
|------|--------|--------|
| User adoption | Active shop owners | 5 in first month |
| User satisfaction | NPS score | > 30 |
| Retention | Weekly active users | > 60% after 2 weeks |

---

## 3. User Personas

### Persona 1: Shop Owner (Primary)
- **Name:** Ramesh (example)
- **Age:** 35-55
- **Business:** Family textile/footwear shop
- **Tech skills:** Basic smartphone, uses WhatsApp
- **Pain:** Wastes hours on manual calculations, doesn't know actual profit
- **Goal:** Spend less time on math, more time growing business
- **Quote:** "I just want to know if I'm actually making money"

### Persona 2: Customer (Secondary)
- **Name:** Any customer walking into the shop
- **Interaction:** Receives bill only
- **Needs:** Correct bill, clear pricing
- **Should NOT see:** Cost price, profit margin, stock levels

---

## 4. User Stories

### MVP (Must Have)

| ID | User Story | Acceptance Criteria |
|----|-----------|---------------------|
| US-01 | As a shop owner, I want to add products with name, cost, and quantity | - Can add product with name, cost price, quantity, category |
| US-02 | As a shop owner, I want to auto-calculate retail price from cost | - Enter cost → system adds 30% → shows retail price |
| US-03 | As a shop owner, I want to search products by name | - Type name → results appear in < 2 seconds |
| US-04 | As a shop owner, I want to generate bills for customers | - Select items → system calculates total → shows retail price only |
| US-05 | As a shop owner, I want to see profit on each sale | - After sale, system shows: items, total, profit |
| US-06 | As a shop owner, I want to track stock levels | - Stock decreases automatically when sale is made |
| US-07 | As a shop owner, I want to save purchase lists | - Add items to list → saved on phone → accessible anywhere |

### V2 (Should Have)

| ID | User Story | Acceptance Criteria |
|----|-----------|---------------------|
| US-08 | As a shop owner, I want to see sales history | - View list of all past sales with date, items, profit |
| US-09 | As a shop owner, I want low-stock alerts | - When stock < 5, show warning |
| US-10 | As a shop owner, I want daily/monthly profit summary | - Dashboard shows today's and this month's profit |

### V3 (Could Have)

| ID | User Story | Acceptance Criteria |
|----|-----------|---------------------|
| US-11 | As a shop owner, I want to see old stock alerts | - Items unsold > 60 days get flagged |
| US-12 | As a shop owner, I want to print price labels | - Generate printable labels with item name and retail price |
| US-13 | As a shop owner, I want demand forecasting | - System predicts which items will sell more |

---

## 5. Feature Prioritization

### MVP (Build First)
- [ ] Product CRUD (add, edit, delete products)
- [ ] Auto price calculator (cost + 30% = retail)
- [ ] Product search
- [ ] Bill generation (customer sees retail only)
- [ ] Profit per sale tracking
- [ ] Basic stock tracking
- [ ] Purchase list (cloud-saved)

### V2 (After MVP Feedback)
- [ ] Sales history with filters
- [ ] Low-stock alerts
- [ ] Daily/monthly profit dashboard
- [ ] User authentication (login/signup)

### V3 (Future)
- [ ] Old stock alerts
- [ ] Price label printing
- [ ] Demand forecasting (ML)
- [ ] Multi-store support
- [ ] Supplier integration

---

## 6. Technical Architecture

### System Diagram
```
┌─────────────────────────────────────────────┐
│              USER (Shop Owner)              │
│                   │                         │
│                   ▼                         │
│         ┌─────────────────┐                │
│         │   Web Browser   │                │
│         │   (Mobile)      │                │
│         └────────┬────────┘                │
│                  │                          │
│                  ▼                          │
│         ┌─────────────────┐                │
│         │    Frontend     │                │
│         │  (React/HTML)   │                │
│         └────────┬────────┘                │
│                  │                          │
│                  ▼                          │
│         ┌─────────────────┐                │
│         │    Backend      │                │
│         │  (Flask/FastAPI)│                │
│         └────────┬────────┘                │
│                  │                          │
│                  ▼                          │
│         ┌─────────────────┐                │
│         │    Database     │                │
│         │  (PostgreSQL)   │                │
│         └─────────────────┘                │
└─────────────────────────────────────────────┘
```

### Tech Stack (Decided)
| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React (or HTML/CSS/JS) | Simple, mobile-friendly |
| Backend | Python Flask | Fast to build, you know Python |
| Database | PostgreSQL (or SQLite for MVP) | Reliable, free |
| Hosting | Railway / Render | Free tier available |

### Tech Stack (Not Decided Yet)
- [ ] React vs plain HTML? (React is better for search/dynamic UI)
- [ ] PostgreSQL vs SQLite? (SQLite for MVP, PostgreSQL later)
- [ ] Authentication? (Add in V2)

---

## 7. Open Questions

| # | Question | Answer Needed By |
|---|----------|-----------------|
| 1 | What's the profit % — fixed 30% or configurable per item? | Before building price calculator |
| 2 | Do you sell to other shops (B2B) or only walk-in customers? | Before building billing |
| 3 | Do you need barcode scanning? | Before building product add |
| 4 | How many products do you have approximately? | Before choosing database |
| 5 | Do you want a mobile app or web app (accessed via phone browser)? | Before building frontend |

---

## Appendix

### Glossary
- **MVP:** Minimum Viable Product — the simplest version that solves the core problem
- **PRD:** Product Requirements Document — this document
- **User Story:** A description of a feature from the user's perspective
- **Acceptance Criteria:** Conditions that must be true for the feature to be "done"
- **B2B:** Business to Business (selling to other businesses)
- **B2C:** Business to Consumer (selling to individual consumers)

### References
- User research: Direct interviews with shop owner (Nivedya M S — self)
- Problem validation: Real-world shop operations (Kerala textile/footwear shop)
