def _add_product(client, name, cost, qty):
    return client.post(
        "/api/products", json={"name": name, "cost_price": cost, "quantity": qty}
    ).get_json()["data"]


def test_create_sale_records_profit_and_decrements_stock(auth_client):
    p1 = _add_product(auth_client, "Curtain", 200, 10)
    p2 = _add_product(auth_client, "Sheet", 100, 5)

    res = auth_client.post(
        "/api/sales",
        json={
            "customer_name": "Walk-in",
            "items": [
                {"product_id": p1["id"], "quantity": 2},
                {"product_id": p2["id"], "quantity": 1},
            ],
        },
    )
    assert res.status_code == 201
    s = res.get_json()["data"]
    assert s["total_amount"] == 260.0 * 2 + 130.0
    assert s["total_profit"] == 60.0 * 2 + 30.0
    assert len(s["items"]) == 2

    assert auth_client.get(f"/api/products/{p1['id']}").get_json()["data"]["quantity"] == 8
    assert auth_client.get(f"/api/products/{p2['id']}").get_json()["data"]["quantity"] == 4


def test_create_sale_rejects_insufficient_stock(auth_client):
    p = _add_product(auth_client, "Curtain", 100, 1)
    res = auth_client.post(
        "/api/sales", json={"items": [{"product_id": p["id"], "quantity": 5}]}
    )
    assert res.status_code == 400
    assert auth_client.get(f"/api/products/{p['id']}").get_json()["data"]["quantity"] == 1


def test_create_sale_requires_items(auth_client):
    res = auth_client.post("/api/sales", json={"items": []})
    assert res.status_code == 400


def test_customer_bill_hides_profit(auth_client):
    p = _add_product(auth_client, "Curtain", 100, 5)
    sale_id = auth_client.post(
        "/api/sales", json={"items": [{"product_id": p["id"], "quantity": 1}]}
    ).get_json()["data"]["id"]
    bill = auth_client.get(f"/api/sales/{sale_id}/bill").get_json()["data"]
    assert "total_profit" not in bill
    for item in bill["items"]:
        assert "unit_cost" not in item
        assert "profit" not in item


def test_today_summary(auth_client):
    p = _add_product(auth_client, "X", 100, 10)
    auth_client.post("/api/sales", json={"items": [{"product_id": p["id"], "quantity": 2}]})
    res = auth_client.get("/api/sales/today")
    data = res.get_json()["data"]
    assert data["count"] == 1
    assert data["total_amount"] == 260.0
    assert data["total_profit"] == 60.0


def test_dashboard(auth_client):
    p = _add_product(auth_client, "X", 100, 3)
    auth_client.post("/api/sales", json={"items": [{"product_id": p["id"], "quantity": 1}]})
    res = auth_client.get("/api/dashboard")
    d = res.get_json()["data"]
    assert d["today"]["sale_count"] == 1
    assert d["today"]["total_amount"] == 130.0
    assert d["stock"]["total_units"] == 2
    assert len(d["last_7_days"]) == 7
