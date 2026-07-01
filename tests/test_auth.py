def test_register_creates_user_and_logs_in(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "u1", "email": "u1@e.com", "password": "secret123"},
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["email"] == "u1@e.com"
    assert body["data"]["profit_percentage"] == 30.0

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["data"]["email"] == "u1@e.com"


def test_register_validation(client):
    res = client.post("/api/auth/register", json={"username": "", "email": "x", "password": "123"})
    assert res.status_code == 400


def test_register_duplicate_email(client):
    body = {"username": "u1", "email": "u1@e.com", "password": "secret123"}
    client.post("/api/auth/register", json=body)
    client.post("/api/auth/logout")
    res = client.post(
        "/api/auth/register",
        json={"username": "u2", "email": "u1@e.com", "password": "secret123"},
    )
    assert res.status_code == 409


def test_login_logout(client, registered_user):
    client.post("/api/auth/logout")
    res = client.post(
        "/api/auth/login",
        json={"email": "ramesh@example.com", "password": "secret123"},
    )
    assert res.status_code == 200
    res = client.post("/api/auth/login", json={"email": "ramesh@example.com", "password": "wrong"})
    assert res.status_code == 401


def test_unauth_requires_login(client):
    res = client.get("/api/products")
    assert res.status_code == 401


def test_update_profile_profit_percentage(auth_client):
    res = auth_client.put("/api/auth/me", json={"profit_percentage": 40})
    assert res.status_code == 200
    assert res.get_json()["data"]["profit_percentage"] == 40.0
