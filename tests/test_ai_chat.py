import os
import tempfile


def _add(client, name="Curtain", cost=100, qty=10):
    return client.post(
        "/api/products", json={"name": name, "cost_price": cost, "quantity": qty}
    ).get_json()["data"]


def test_ai_status_reports_stub_mode(auth_client):
    r = auth_client.get("/api/ai/status").get_json()["data"]
    assert r["provider"] == "stub"
    assert r["stub_mode"] is True
    assert isinstance(r["example_questions"], list) and len(r["example_questions"]) > 0


def test_chat_requires_question(auth_client):
    r = auth_client.post("/api/ai/chat", json={})
    assert r.status_code == 400


def test_chat_requires_file_backed_db(auth_client):
    # Test config uses :memory: — should refuse.
    r = auth_client.post("/api/ai/chat", json={"question": "How many products?"})
    assert r.status_code == 400
    assert "file-backed" in r.get_json()["error"]


def _file_backed_client_pair():
    """Build a fresh app + client using a real file DB so /api/ai/chat runs."""
    import pytest  # noqa

    from backend import create_app
    from backend.config import Config
    from backend.database.db import db

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    class FileDbConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{path}"
        TESTING = True
        SECRET_KEY = "t"
        LLM_PROVIDER = "stub"
        WTF_CSRF_ENABLED = False

    app = create_app(FileDbConfig)

    def cleanup():
        with app.app_context():
            db.session.remove()
        try:
            os.unlink(path)
        except OSError:
            pass

    return app, app.test_client(), cleanup


def test_chat_end_to_end_with_stub():
    app, client, cleanup = _file_backed_client_pair()
    try:
        client.post(
            "/api/auth/register",
            json={"username": "n", "email": "n@e.com", "password": "secret123"},
        )
        # Seed some data via the API so the FKs & views work.
        _add(client, "Blue Curtain", 100, 12)
        _add(client, "White Sheet", 50, 3)
        client.post(
            "/api/sales",
            json={
                "customer_name": "Test",
                "items": [{"product_id": 1, "quantity": 2}],
            },
        )

        # "How many products do I have?" → stub matches this pattern.
        r = client.post("/api/ai/chat", json={"question": "How many products do I have?"})
        assert r.status_code == 200, r.get_json()
        d = r.get_json()["data"]
        assert d["used_stub"] is True
        assert d["sql"]
        assert "SELECT COUNT" in d["sql"].upper()
        assert d["result"]["rows"][0][0] == 2  # two products
        assert d["answer"]

        # "Which items are low stock?" → stub returns a listing query.
        r = client.post("/api/ai/chat", json={"question": "Which items are low stock?"})
        d = r.get_json()["data"]
        assert d["sql"]
        names = [row[0] for row in d["result"]["rows"]]
        assert "White Sheet" in names

        # Unknown question → stub replies with a helpful "not understood" answer.
        r = client.post("/api/ai/chat", json={"question": "What is the meaning of life?"})
        d = r.get_json()["data"]
        assert d["used_stub"] is True
        assert "stub mode" in d["answer"]

    finally:
        cleanup()


def test_chat_data_scoped_to_current_user():
    app, client, cleanup = _file_backed_client_pair()
    try:
        client.post(
            "/api/auth/register",
            json={"username": "a", "email": "a@e.com", "password": "secret123"},
        )
        _add(client, "Alice Only 1")
        _add(client, "Alice Only 2")
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/register",
            json={"username": "b", "email": "b@e.com", "password": "secret123"},
        )
        _add(client, "Bob Only 1")

        r = client.post("/api/ai/chat", json={"question": "How many products do I have?"})
        d = r.get_json()["data"]
        assert d["result"]["rows"][0][0] == 1  # Bob sees only their own row

    finally:
        cleanup()
