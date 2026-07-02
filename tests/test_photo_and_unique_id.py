import io
import os
import shutil

import pytest


TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63f8cf000000030001010060fabc0000000049454e"
    "44ae426082"
)


@pytest.fixture
def upload_dir(app):
    d = app.config["UPLOAD_FOLDER"]
    os.makedirs(d, exist_ok=True)
    yield d
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def _add(client, name="Curtain", cost=100, qty=10):
    r = client.post(
        "/api/products", json={"name": name, "cost_price": cost, "quantity": qty}
    )
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def test_first_product_gets_instox_00001(auth_client):
    p = _add(auth_client, "First")
    assert p["unique_id"] == "INSTOX-00001"


def test_unique_ids_are_sequential(auth_client):
    ids = [_add(auth_client, f"P{i}")["unique_id"] for i in range(3)]
    assert ids == ["INSTOX-00001", "INSTOX-00002", "INSTOX-00003"]


def test_search_matches_by_unique_id(auth_client):
    _add(auth_client, "A")
    _add(auth_client, "B")
    r = auth_client.get("/api/products/search?q=INSTOX-00002").get_json()["data"]
    assert len(r) == 1
    assert r[0]["name"] == "B"

    r = auth_client.get("/api/products/search?q=instox-00001").get_json()["data"]
    assert len(r) == 1
    assert r[0]["name"] == "A"


def test_list_search_matches_by_unique_id(auth_client):
    _add(auth_client, "A")
    _add(auth_client, "B")
    r = auth_client.get("/api/products?search=INSTOX-00002").get_json()["data"]
    assert [p["name"] for p in r] == ["B"]


def test_product_response_includes_photo_url_null_by_default(auth_client):
    p = _add(auth_client, "NoPhoto")
    assert p["photo_url"] is None


def test_photo_upload_success(auth_client, upload_dir):
    p = _add(auth_client, "WithPhoto")
    res = auth_client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(TINY_PNG), "shot.png")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200, res.get_json()
    data = res.get_json()["data"]
    assert data["photo_url"] is not None
    assert data["photo_url"].startswith("/uploads/product_")
    assert data["photo_url"].endswith(".png")

    saved_name = os.path.basename(data["photo_url"])
    assert os.path.isfile(os.path.join(upload_dir, saved_name))


def test_photo_upload_rejects_bad_extension(auth_client, upload_dir):
    p = _add(auth_client)
    res = auth_client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(b"not an image"), "evil.exe")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "Unsupported" in res.get_json()["error"]


def test_photo_upload_requires_file(auth_client):
    p = _add(auth_client)
    res = auth_client.post(f"/api/products/{p['id']}/photo", data={})
    assert res.status_code == 400


def test_photo_upload_replaces_old_and_deletes_file(auth_client, upload_dir):
    p = _add(auth_client)

    r1 = auth_client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(TINY_PNG), "first.png")},
        content_type="multipart/form-data",
    )
    first_name = os.path.basename(r1.get_json()["data"]["photo_url"])
    assert os.path.isfile(os.path.join(upload_dir, first_name))

    r2 = auth_client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(TINY_PNG), "second.jpg")},
        content_type="multipart/form-data",
    )
    second_name = os.path.basename(r2.get_json()["data"]["photo_url"])
    assert second_name != first_name
    assert not os.path.isfile(os.path.join(upload_dir, first_name))
    assert os.path.isfile(os.path.join(upload_dir, second_name))


def test_photo_delete(auth_client, upload_dir):
    p = _add(auth_client)
    r = auth_client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(TINY_PNG), "x.png")},
        content_type="multipart/form-data",
    )
    photo_url = r.get_json()["data"]["photo_url"]
    saved = os.path.basename(photo_url)

    res = auth_client.delete(f"/api/products/{p['id']}/photo")
    assert res.status_code == 200
    assert res.get_json()["data"]["photo_url"] is None
    assert not os.path.isfile(os.path.join(upload_dir, saved))


def test_serve_uploaded_photo(auth_client, upload_dir):
    p = _add(auth_client)
    r = auth_client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(TINY_PNG), "x.png")},
        content_type="multipart/form-data",
    )
    url = r.get_json()["data"]["photo_url"]
    served = auth_client.get(url)
    assert served.status_code == 200
    assert served.data == TINY_PNG


def test_photo_upload_scoped_to_owner(client, upload_dir):
    client.post(
        "/api/auth/register",
        json={"username": "a", "email": "a@e.com", "password": "secret123"},
    )
    p = client.post(
        "/api/products", json={"name": "Mine", "cost_price": 10, "quantity": 1}
    ).get_json()["data"]
    client.post("/api/auth/logout")

    client.post(
        "/api/auth/register",
        json={"username": "b", "email": "b@e.com", "password": "secret123"},
    )
    res = client.post(
        f"/api/products/{p['id']}/photo",
        data={"photo": (io.BytesIO(TINY_PNG), "x.png")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 404


def test_migration_backfills_unique_id_on_old_db(tmp_path):
    """Old DB with products but no unique_id column gets it added + backfilled."""
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
            CREATE TABLE categories (id INTEGER PRIMARY KEY, user_id INT, name TEXT);
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category_id INTEGER,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                cost_price NUMERIC(10,2) NOT NULL,
                retail_price NUMERIC(10,2) NOT NULL,
                quantity INTEGER DEFAULT 0,
                sku VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users (username, email, password_hash) VALUES ('u', 'u@e.com', 'x');
            INSERT INTO products (id, user_id, name, cost_price, retail_price, quantity)
              VALUES (1, 1, 'Old A', 100, 130, 5),
                     (2, 1, 'Old B', 200, 260, 3),
                     (17, 1, 'Old C', 50, 65, 1);
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
            cols = [row[1] for row in conn.execute("PRAGMA table_info(products)")]
            assert "unique_id" in cols
            assert "photo_url" in cols
            rows = dict(conn.execute("SELECT id, unique_id FROM products").fetchall())
            assert rows[1] == "INSTOX-00001"
            assert rows[2] == "INSTOX-00002"
            assert rows[17] == "INSTOX-00017"
