def test_purchase_list_crud(auth_client):
    res = auth_client.post("/api/purchase-list", json={"item_name": "Blue cotton 6x8", "quantity": 3})
    assert res.status_code == 201
    item = res.get_json()["data"]
    assert item["item_name"] == "Blue cotton 6x8"
    assert item["is_purchased"] is False

    res = auth_client.put(f"/api/purchase-list/{item['id']}", json={"is_purchased": True})
    assert res.get_json()["data"]["is_purchased"] is True

    items = auth_client.get("/api/purchase-list").get_json()["data"]
    assert len(items) == 1

    auth_client.delete(f"/api/purchase-list/{item['id']}")
    items = auth_client.get("/api/purchase-list").get_json()["data"]
    assert items == []


def test_purchase_list_requires_name(auth_client):
    res = auth_client.post("/api/purchase-list", json={"item_name": ""})
    assert res.status_code == 400
