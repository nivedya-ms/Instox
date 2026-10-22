"""Tests for the batch of small fixes:
- top-5 recent products (?sort=recent)
- category unit + icon columns
- default categories seeded on registration
- pwa endpoints (manifest.json, sw.js)
- reports.html removed
"""

import time


def _add(client, name, cost=100, qty=1):
    return client.post(
        "/api/products", json={"name": name, "cost_price": cost, "quantity": qty}
    ).get_json()["data"]


def test_default_categories_seeded_on_registration(client):
    client.post(
        "/api/auth/register",
        json={"username": "seed", "email": "seed@e.com", "password": "secret123"},
    )
    cats = client.get("/api/categories").get_json()["data"]
    names = {c["name"] for c in cats}
    assert "Curtains" in names
    assert "Running Material" in names
    assert "Footwear" in names
    assert "Other" in names

    # Units are populated
    by_name = {c["name"]: c for c in cats}
    assert by_name["Running Material"]["unit"] == "meters"
    assert by_name["Footwear"]["unit"] == "pairs"
    assert by_name["Curtains"]["unit"] == "pieces"
    # Icons too
    assert by_name["Footwear"]["icon"] == "👟"


def test_category_unit_and_icon_can_be_customized(auth_client):
    r = auth_client.post(
        "/api/categories",
        json={"name": "Kg Rice", "unit": "kg", "icon": "🍚"},
    )
    assert r.status_code == 201
    d = r.get_json()["data"]
    assert d["unit"] == "kg"
    assert d["icon"] == "🍚"

    r = auth_client.put(
        f"/api/categories/{d['id']}",
        json={"unit": "litres", "icon": "🍶"},
    )
    d = r.get_json()["data"]
    assert d["unit"] == "litres"
    assert d["icon"] == "🍶"


def test_product_response_carries_category_unit(auth_client):
    cat = auth_client.post(
        "/api/categories", json={"name": "Meters", "unit": "meters", "icon": "🧵"}
    ).get_json()["data"]
    p = auth_client.post(
        "/api/products",
        json={"name": "Silk", "cost_price": 500, "quantity": 8, "category_id": cat["id"]},
    ).get_json()["data"]
    assert p["unit"] == "meters"
    assert p["category_name"] == "Meters"


def test_product_response_defaults_to_pieces_when_no_category(auth_client):
    p = _add(auth_client, "No cat")
    assert p["unit"] == "pieces"


def test_products_sort_recent_returns_newest_first(auth_client):
    _add(auth_client, "First")
    time.sleep(0.01)
    _add(auth_client, "Second")
    time.sleep(0.01)
    _add(auth_client, "Third")
    r = auth_client.get("/api/products?sort=recent&limit=5").get_json()["data"]
    assert [p["name"] for p in r] == ["Third", "Second", "First"]


def test_products_default_sort_is_by_name(auth_client):
    _add(auth_client, "Zebra")
    _add(auth_client, "Alpha")
    r = auth_client.get("/api/products").get_json()["data"]
    names = [p["name"] for p in r]
    assert names.index("Alpha") < names.index("Zebra")


def test_pwa_manifest_served(client):
    r = client.get("/manifest.json")
    assert r.status_code == 200
    body = r.get_json()
    assert body["name"].startswith("Instox")
    assert body["display"] == "standalone"


def test_pwa_service_worker_served(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert b"instox-v1" in r.data or b"CACHE_VERSION" in r.data


def test_reports_page_removed(client):
    r = client.get("/reports.html")
    assert r.status_code == 404


def test_chat_page_served(client):
    r = client.get("/chat.html")
    assert r.status_code == 200
    assert b"Ask about your shop" in r.data


def test_migration_adds_unit_and_icon_to_old_categories(tmp_path):
    """Old DB with a pre-existing categories table gets unit + icon columns added."""
    import sqlite3

    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE,
                password_hash TEXT, shop_name TEXT,
                profit_percentage NUMERIC(5,2) DEFAULT 30.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                name TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users (username, email, password_hash) VALUES ('u', 'u@e.com', 'x');
            INSERT INTO categories (user_id, name) VALUES (1, 'Old Cat');
            """
        )

    from backend import create_app
    from backend.config import Config

    class OldDbConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        TESTING = True
        SECRET_KEY = "t"

    app = create_app(OldDbConfig)
    with app.app_context():
        with sqlite3.connect(db_path) as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(categories)")]
            assert "unit" in cols
            assert "icon" in cols
            row = conn.execute("SELECT unit, icon FROM categories WHERE name='Old Cat'").fetchone()
            assert row == ("pieces", "📦")
