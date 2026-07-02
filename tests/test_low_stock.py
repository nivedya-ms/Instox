def _add(client, name, qty):
    return client.post(
        "/api/products", json={"name": name, "cost_price": 100, "quantity": qty}
    ).get_json()["data"]


def test_default_threshold_is_five(auth_client):
    me = auth_client.get("/api/auth/me").get_json()["data"]
    assert me["low_stock_threshold"] == 5

    s = auth_client.get("/api/settings").get_json()["data"]
    assert s["low_stock_threshold"] == 5


def test_low_stock_uses_user_threshold_by_default(auth_client):
    _add(auth_client, "Plenty", 20)
    _add(auth_client, "Low1", 3)
    _add(auth_client, "Low2", 5)
    _add(auth_client, "Empty", 0)

    r = auth_client.get("/api/products/low-stock").get_json()["data"]
    assert r["threshold"] == 5
    names = {p["name"] for p in r["items"]}
    assert names == {"Low1", "Low2", "Empty"}
    assert r["out_of_stock_count"] == 1
    assert r["low_count"] == 2
    assert r["out_of_stock"][0]["name"] == "Empty"


def test_low_stock_respects_query_override(auth_client):
    _add(auth_client, "A", 3)
    _add(auth_client, "B", 8)
    r = auth_client.get("/api/products/low-stock?threshold=10").get_json()["data"]
    assert r["threshold"] == 10
    assert {p["name"] for p in r["items"]} == {"A", "B"}


def test_low_stock_rejects_negative_threshold(auth_client):
    res = auth_client.get("/api/products/low-stock?threshold=-1")
    assert res.status_code == 400


def test_update_threshold_via_settings(auth_client):
    res = auth_client.put("/api/settings/threshold", json={"low_stock_threshold": 3})
    assert res.status_code == 200
    assert res.get_json()["data"]["low_stock_threshold"] == 3

    _add(auth_client, "Q4", 4)
    _add(auth_client, "Q2", 2)
    r = auth_client.get("/api/products/low-stock").get_json()["data"]
    assert r["threshold"] == 3
    assert {p["name"] for p in r["items"]} == {"Q2"}


def test_update_threshold_validation(auth_client):
    assert auth_client.put("/api/settings/threshold", json={"low_stock_threshold": -1}).status_code == 400
    assert auth_client.put("/api/settings/threshold", json={"low_stock_threshold": "abc"}).status_code == 400


def test_update_settings_bulk(auth_client):
    res = auth_client.put(
        "/api/settings",
        json={"low_stock_threshold": 7, "profit_percentage": 25, "shop_name": "New Name"},
    )
    d = res.get_json()["data"]
    assert d["low_stock_threshold"] == 7
    assert d["profit_percentage"] == 25.0
    assert d["shop_name"] == "New Name"


def test_product_response_includes_stock_status(auth_client):
    p = _add(auth_client, "Item", 3)
    assert p["stock_status"] == "low"
    p2 = _add(auth_client, "Zero", 0)
    assert p2["stock_status"] == "out_of_stock"
    p3 = _add(auth_client, "Plenty", 20)
    assert p3["stock_status"] == "normal"


def test_dashboard_includes_categorized_alerts(auth_client):
    _add(auth_client, "Plenty", 20)
    _add(auth_client, "Low", 3)
    _add(auth_client, "Empty", 0)

    d = auth_client.get("/api/dashboard").get_json()["data"]
    stock = d["stock"]
    assert stock["threshold"] == 5
    assert stock["low_stock_count"] == 2
    assert stock["out_of_stock_count"] == 1
    assert stock["low_only_count"] == 1
    assert [p["name"] for p in stock["out_of_stock"]] == ["Empty"]
    assert [p["name"] for p in stock["low"]] == ["Low"]


def test_dashboard_alerts_react_to_threshold_change(auth_client):
    _add(auth_client, "P8", 8)
    assert auth_client.get("/api/dashboard").get_json()["data"]["stock"]["low_stock_count"] == 0
    auth_client.put("/api/settings/threshold", json={"low_stock_threshold": 10})
    d = auth_client.get("/api/dashboard").get_json()["data"]
    assert d["stock"]["threshold"] == 10
    assert d["stock"]["low_stock_count"] == 1
    assert d["stock"]["low"][0]["name"] == "P8"


def test_threshold_column_migration_adds_column_to_existing_db(tmp_path):
    """Simulate an old DB without low_stock_threshold; app startup should backfill it."""
    import sqlite3

    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                shop_name VARCHAR(100),
                profit_percentage NUMERIC(5,2) DEFAULT 30.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users (username, email, password_hash) VALUES ('u', 'u@e.com', 'x');
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
            cols = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
            assert "low_stock_threshold" in cols
            (val,) = conn.execute("SELECT low_stock_threshold FROM users").fetchone()
            assert val == 5
