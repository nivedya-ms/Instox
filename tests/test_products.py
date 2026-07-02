def test_create_product_auto_calculates_retail(auth_client):
    res = auth_client.post(
        "/api/products",
        json={"name": "Blue Curtain 6x8", "cost_price": 200, "quantity": 10},
    )
    assert res.status_code == 201
    p = res.get_json()["data"]
    assert p["name"] == "Blue Curtain 6x8"
    assert p["cost_price"] == 200.0
    assert p["retail_price"] == 260.0
    assert p["quantity"] == 10


def test_create_product_requires_name(auth_client):
    res = auth_client.post("/api/products", json={"name": "", "cost_price": 100, "quantity": 1})
    assert res.status_code == 400


def test_calculate_price_endpoint(auth_client):
    res = auth_client.post("/api/products/calculate-price", json={"cost_price": 500, "set_size": 5})
    body = res.get_json()
    assert body["data"]["unit_cost"] == 100.0
    assert body["data"]["retail_price"] == 130.0


def test_search_products(auth_client):
    auth_client.post("/api/products", json={"name": "Blue Curtain 6x8", "cost_price": 200, "quantity": 10})
    auth_client.post("/api/products", json={"name": "White Sheet 4x6", "cost_price": 100, "quantity": 5})
    res = auth_client.get("/api/products/search?q=blue")
    data = res.get_json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Blue Curtain 6x8"


def test_search_no_results(auth_client):
    res = auth_client.get("/api/products/search?q=nonexistent")
    assert res.get_json()["data"] == []


def test_update_product_recalculates_retail_on_cost_change(auth_client):
    pid = auth_client.post(
        "/api/products", json={"name": "X", "cost_price": 100, "quantity": 1}
    ).get_json()["data"]["id"]
    res = auth_client.put(f"/api/products/{pid}", json={"cost_price": 200})
    p = res.get_json()["data"]
    assert p["cost_price"] == 200.0
    assert p["retail_price"] == 260.0


def test_delete_product(auth_client):
    pid = auth_client.post(
        "/api/products", json={"name": "X", "cost_price": 10, "quantity": 1}
    ).get_json()["data"]["id"]
    assert auth_client.delete(f"/api/products/{pid}").status_code == 200
    assert auth_client.get(f"/api/products/{pid}").status_code == 404


def test_low_stock(auth_client):
    auth_client.post("/api/products", json={"name": "A", "cost_price": 1, "quantity": 2})
    auth_client.post("/api/products", json={"name": "B", "cost_price": 1, "quantity": 10})
    res = auth_client.get("/api/products/low-stock?threshold=5")
    data = res.get_json()["data"]
    names = [p["name"] for p in data["items"]]
    assert names == ["A"]
    assert data["threshold"] == 5


def test_users_cannot_see_each_others_products(client):
    client.post(
        "/api/auth/register",
        json={"username": "u1", "email": "u1@e.com", "password": "secret123"},
    )
    client.post("/api/products", json={"name": "Private", "cost_price": 10, "quantity": 1})
    client.post("/api/auth/logout")

    client.post(
        "/api/auth/register",
        json={"username": "u2", "email": "u2@e.com", "password": "secret123"},
    )
    res = client.get("/api/products")
    assert res.get_json()["data"] == []
