# V3 Implementation Plan
## Instox — Photo Capture, Auto ID, Category Browsing, Suppliers, Multi-User

**Date:** July 2026
**Status:** Ready for Implementation

---

## Table of Contents

1. [V3 Feature Overview](#1-v3-feature-overview)
2. [Feature 1: Photo Capture](#2-feature-1-photo-capture)
3. [Feature 2: Auto Unique ID](#3-feature-2-auto-unique-id)
4. [Feature 3: Category Browsing](#4-feature-3-category-browsing)
5. [Feature 4: Search Enhancement](#5-feature-4-search-enhancement)
6. [Feature 5: Supplier Management](#6-feature-5-supplier-management)
7. [Feature 6: Multi-User Support](#7-feature-6-multi-user-support)
8. [Database Changes](#8-database-changes)
9. [API Changes](#9-api-changes)
10. [Frontend Changes](#10-frontend-changes)
11. [Implementation Order](#11-implementation-order)
12. [Claude Code Prompt](#12-claude-code-prompt)

---

## 1. V3 Feature Overview

| # | Feature | Description | User Value |
|---|---------|-------------|------------|
| 1 | Photo capture | Take picture of product with phone camera | Visual reference for products |
| 2 | Auto unique ID | System generates INSTOX-XXXXX for each product | Easy identification and lookup |
| 3 | Category browsing | Click category to see all items | Faster navigation |
| 4 | Search enhancement | Show photo + ID in search results | Visual product identification |
| 5 | Supplier management | Track who you buy from | Know your suppliers |
| 6 | Multi-user support | Family members can use same account | Shared access for family businesses |

---

## 2. Feature 1: Photo Capture

### What It Does
Allows shop owners to take a photo of a product when adding it to inventory.

### User Story
**As a** shop owner,
**I want to** take a photo of a product when adding it,
**so that** I have a visual reference for future lookup.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I add a new product | I tap "Take Photo" | Phone camera opens |
| 2 | I take a photo | I confirm | Photo is saved with product |
| 3 | I view product list | Any time | Photo thumbnail is shown |
| 4 | I search for product | Results show | Photo is shown in results |
| 5 | I don't have a photo | I skip photo | Product saves without photo |

### Implementation Details

**Frontend (HTML):**
```html
<!-- Camera input for mobile -->
<input type="file" 
       id="product-photo" 
       accept="image/*" 
       capture="environment"
       class="form-control">

<!-- Preview before upload -->
<img id="photo-preview" src="" alt="Preview" style="display:none;">
```

**Backend (Flask):**
```python
# Save photo to uploads folder
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'backend/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def save_photo(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return f'/uploads/{filename}'
    return None
```

**File Structure:**
```
instox/
├── backend/
│   └── uploads/          ← Photos stored here
│       ├── product_001.jpg
│       ├── product_002.jpg
│       └── ...
```

---

## 3. Feature 2: Auto Unique ID

### What It Does
Automatically generates a unique ID for each product in format INSTOX-XXXXX.

### User Story
**As a** shop owner,
**I want to** each product to have a unique ID,
**so that** I can easily identify and reference products.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I create a new product | Product is saved | System assigns ID like INSTOX-00123 |
| 2 | ID is generated | On creation | ID is sequential (00001, 00002, etc.) |
| 3 | ID is displayed | In product list | ID is shown above product name |
| 4 | ID is searchable | In search | I can search by ID |

### ID Generation Logic

```python
import random

def generate_unique_id():
    # Get last product ID from database
    last_product = Product.query.order_by(Product.id.desc()).first()
    
    if last_product:
        next_number = last_product.id + 1
    else:
        next_number = 1
    
    # Format: INSTOX-00001
    return f"INSTOX-{next_number:05d}"
```

**Examples:**
- First product: INSTOX-00001
- Second product: INSTOX-00002
- Hundredth product: INSTOX-00100

---

## 4. Feature 3: Category Browsing

### What It Does
Allows users to browse products by category.

### User Story
**As a** shop owner,
**I want to** browse products by category,
**so that** I can quickly find items in a specific group.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I view categories page | Any time | Shows all categories with product count |
| 2 | I click a category | Click event | Shows all products in that category |
| 3 | I have 50 curtain products | I click "Curtains" | Shows 50 curtain products |
| 4 | Category has 0 products | I click category | Shows "No products in this category" |

### Categories Page

```
┌─────────────────────────────────────┐
│ 📂 CATEGORIES                       │
│ ─────────────────────────────────── │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🏠 Curtains                     │ │
│ │ 45 products                     │ │
│ │ [View Products →]               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 👕 Fabrics                      │ │
│ │ 32 products                     │ │
│ │ [View Products →]               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 👟 Footwear                     │ │
│ │ 28 products                     │ │
│ │ [View Products →]               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🎀 Accessories                  │ │
│ │ 15 products                     │ │
│ │ [View Products →]               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🛏️ Home Textiles               │ │
│ │ 12 products                     │ │
│ │ [View Products →]               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 📦 Other                        │ │
│ │ 8 products                      │ │
│ │ [View Products →]               │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## 5. Feature 4: Search Enhancement

### What It Does
Enhances search to show photos and unique IDs.

### User Story
**As a** shop owner,
**I want to** see photos and IDs in search results,
**so that** I can quickly identify products.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I search for "blue curtain" | Results show | Each result shows photo thumbnail |
| 2 | I search for "INSTOX-00123" | Results show | Product with that ID is found |
| 3 | Product has no photo | Results show | Default placeholder image shown |
| 4 | I filter by category | Results show | Only products in that category |

### Enhanced Search Results

```
┌─────────────────────────────────────┐
│ 🔍 SEARCH: "blue curtain"           │
│ ─────────────────────────────────── │
│                                     │
│ Category: [All ▼]                  │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 📷 INSTOX-00123                │ │
│ │ Blue Curtain 6x8               │ │
│ │ ₹260 | Stock: 12              │ │
│ │ Category: Curtains             │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 📷 INSTOX-00124                │ │
│ │ Blue Curtain 4x6               │ │
│ │ ₹180 | Stock: 8               │ │
│ │ Category: Curtains             │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Found 2 products (0.3 seconds)     │
└─────────────────────────────────────┘
```

---

## 6. Feature 5: Supplier Management

### What It Does
Allows shop owners to track their suppliers.

### User Story
**As a** shop owner,
**I want to** manage my suppliers,
**so that** I know who I buy from and can contact them easily.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I add a supplier | I enter name, phone, address | Supplier is saved |
| 2 | I add a product | I select a supplier | Product is linked to supplier |
| 3 | I view supplier list | Any time | Shows all suppliers |
| 4 | I click a supplier | Click event | Shows all products from that supplier |
| 5 | I edit supplier | I change details | Supplier is updated |

### Supplier Management Page

```
┌─────────────────────────────────────┐
│ 🏪 SUPPLIERS                        │
│ ─────────────────────────────────── │
│                                     │
│ [+ Add Supplier]                   │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ ABC Textiles                   │ │
│ │ 📞 9876543210                  │ │
│ │ 📍 Ernakulam, Kerala           │ │
│ │ Products: 25                   │ │
│ │ [Edit] [View Products]         │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ XYZ Fabrics                    │ │
│ │ 📞 9876543211                  │ │
│ │ 📍 Thrissur, Kerala            │ │
│ │ Products: 18                   │ │
│ │ [Edit] [View Products]         │ │
│ └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

---

## 7. Feature 6: Multi-User Support

### What It Does
Allows family members to share the same account.

### User Story
**As a** shop owner,
**I want to** add my family members as users,
**so that** they can help manage the shop.

### Acceptance Criteria

| # | Given | When | Then |
|---|-------|------|------|
| 1 | I am the owner | I login | I see "Manage Users" option |
| 2 | I add a family member | I enter their name and role | They can access the app |
| 3 | Family member logs in | They use their credentials | They can add products and make sales |
| 4 | Owner views user list | Any time | Shows all users with roles |
| 5 | Owner removes a user | I click remove | User loses access |

### User Roles

| Role | Can Do | Cannot Do |
|------|--------|-----------|
| **Owner** | Everything (add users, delete products, view reports) | — |
| **Family Member** | Add products, make sales, view inventory | Delete products, manage users, view profit reports |

### User Management Page

```
┌─────────────────────────────────────┐
│ 👥 MANAGE USERS                     │
│ ─────────────────────────────────── │
│                                     │
│ [+ Add User]                       │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 👤 Ramesh (Owner)              │ │
│ │ 📧 ramesh@email.com            │ │
│ │ Role: Owner                    │ │
│ │ Joined: Jan 2026               │ │
│ │ [Edit]                         │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐
│ │ 👤 Suresh (Family Member)      │ │
│ │ 📧 suresh@email.com            │ │
│ │ Role: Family Member            │ │
│ │ Joined: Mar 2026               │ │
│ │ [Edit] [Remove]                │ │
│ └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

---

## 8. Database Changes

### Products Table (Add columns)

```sql
ALTER TABLE products ADD COLUMN photo_url VARCHAR(255);
ALTER TABLE products ADD COLUMN unique_id VARCHAR(20) UNIQUE;
ALTER TABLE products ADD COLUMN supplier_id INTEGER;
ALTER TABLE products ADD FOREIGN KEY (supplier_id) REFERENCES suppliers(id);
```

### New Table: suppliers

```sql
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### New Table: users (multi-user)

```sql
CREATE TABLE app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'family_member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
```

### Updated Categories Table

```sql
-- Pre-defined categories for small shops
INSERT INTO categories (name, description) VALUES
('Curtains', 'All types of curtains and drapes'),
('Fabrics', 'Raw fabrics and materials'),
('Footwear', 'Shoes, chappals, sandals'),
('Accessories', 'Buttons, threads, laces, etc.'),
('Home Textiles', 'Bedsheets, pillowcases, towels'),
('Other', 'Miscellaneous items');
```

---

## 9. API Endpoints

### Photo Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/products/:id/photo` | Upload photo for product |
| GET | `/api/uploads/:filename` | Get uploaded photo |

### Unique ID

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/:id/unique-id` | Get unique ID for product |

### Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | List all categories with product count |
| GET | `/api/categories/:id/products` | Get products in category |

### Suppliers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/suppliers` | List all suppliers |
| POST | `/api/suppliers` | Add supplier |
| PUT | `/api/suppliers/:id` | Update supplier |
| DELETE | `/api/suppliers/:id` | Delete supplier |
| GET | `/api/suppliers/:id/products` | Get products from supplier |

### Multi-User

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List all users |
| POST | `/api/users` | Add user |
| PUT | `/api/users/:id` | Update user |
| DELETE | `/api/users/:id` | Remove user |

---

## 10. Frontend Changes

### New Files

| File | Purpose |
|------|---------|
| `frontend/categories.html` | Categories browsing page |
| `frontend/suppliers.html` | Supplier management page |
| `frontend/users.html` | User management page |
| `frontend/js/categories.js` | Categories logic |
| `frontend/js/suppliers.js` | Suppliers logic |
| `frontend/js/users.js` | Users logic |
| `frontend/js/photo.js` | Photo capture logic |

### Modified Files

| File | Changes |
|------|---------|
| `frontend/product_form.html` | Add camera input, preview |
| `frontend/products.html` | Show photo thumbnails, unique ID |
| `frontend/products.html` | Add category filter dropdown |
| `frontend/index.html` | Add navigation links |
| `frontend/css/style.css` | Add photo styles |

---

## 11. Implementation Order

| Day | Feature | Tasks |
|-----|---------|-------|
| Day 1 | Photo capture | Camera input, upload, storage, preview |
| Day 2 | Auto unique ID | ID generation, display, search |
| Day 3 | Category browsing | Categories page, product filtering |
| Day 4 | Search enhancement | Show photos, IDs, category filter |
| Day 5 | Supplier management | CRUD, link products |
| Day 6 | Multi-user support | User management, roles |
| Day 7 | Test + deploy | Bug fixes, push to GitHub |

---

## 12. Claude Code Prompt

```
Read docs/V2_IMPLEMENTATION_PLAN.md for context on what's already built.

Now implement V3 features:

1. Photo capture:
   - Add camera input to product form (HTML: <input type="file" accept="image/*" capture="environment">)
   - Save uploaded photo to /backend/uploads/
   - Display photo thumbnail on product cards and search results

2. Auto unique ID:
   - Generate ID on product creation: format INSTOX-XXXXX (e.g., INSTOX-00123)
   - Store in products table (unique_id column)
   - Display in product list and search results

3. Category browsing:
   - Create categories page: frontend/categories.html
   - Show category cards with product count
   - Click category → show all products in that category
   - Add navigation link

4. Search enhancement:
   - Update search to show photo thumbnail
   - Show unique ID in results
   - Filter by category

5. Supplier management:
   - Create suppliers table
   - CRUD for suppliers (name, phone, address)
   - Link products to suppliers
   - Add supplier field in product form
   - Show supplier in product details

6. Multi-user support:
   - Create app_users table with roles (owner, family_member)
   - Add user management page
   - Owner can add family members
   - Family members can add products and make sales

Test all features after implementation.
```

---

**END OF V3 IMPLEMENTATION PLAN**
