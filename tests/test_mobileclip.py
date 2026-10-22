"""Tests for MobileCLIP wiring.

The model download takes ~30 s on first use; these tests skip themselves
when the model can't be loaded (e.g. no network), so CI in an offline env
stays green.
"""

import io
import os
import shutil

import numpy as np
import pytest
from PIL import Image

from backend.services import mobileclip


TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63f8cf000000030001010060fabc0000000049454e"
    "44ae426082"
)


def _png(color=(100, 100, 100), size=(256, 256)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _mobileclip_ready() -> bool:
    """Try to load once. Returns True if ready. Marks tests as skipped
    when the model can't be downloaded / loaded."""
    return mobileclip.ensure_ready()


needs_mobileclip = pytest.mark.skipif(
    not _mobileclip_ready(),
    reason="MobileCLIP model not available (no network or download failed)",
)


# --- unit-ish -------------------------------------------------------------


def test_status_shape_always_valid():
    s = mobileclip.status()
    assert isinstance(s.ready, bool)
    assert isinstance(s.loading, bool)
    assert s.embedding_dim == 512
    assert s.image_size == 256


@needs_mobileclip
def test_embed_returns_normalized_512dim_vector():
    v = mobileclip.embed(_png())
    assert v.shape == (512,)
    assert v.dtype == np.float32
    assert abs(np.linalg.norm(v) - 1.0) < 1e-4


@needs_mobileclip
def test_similar_photos_score_higher_than_dissimilar():
    red = _png(color=(200, 20, 20))
    red2 = _png(color=(220, 30, 30))  # near-identical
    blue = _png(color=(20, 20, 200))
    e_red, e_red2, e_blue = mobileclip.embed(red), mobileclip.embed(red2), mobileclip.embed(blue)
    assert mobileclip.cosine_similarity(e_red, e_red2) > mobileclip.cosine_similarity(e_red, e_blue)


@needs_mobileclip
def test_to_bytes_from_bytes_roundtrip():
    v = mobileclip.embed(_png())
    blob = mobileclip.to_bytes(v)
    assert len(blob) == 512 * 4  # float32
    v2 = mobileclip.from_bytes(blob)
    assert np.allclose(v, v2)


@needs_mobileclip
def test_rank_puts_query_first_when_query_is_a_candidate():
    v = mobileclip.embed(_png(color=(80, 200, 40)))
    others = [
        (i, mobileclip.embed(_png(color=(i * 30 % 255, i * 55 % 255, i * 90 % 255))))
        for i in range(1, 5)
    ]
    ranked = mobileclip.rank(v, [(0, v)] + others, top_n=3)
    assert ranked[0].product_id == 0
    assert ranked[0].similarity == pytest.approx(1.0, abs=1e-3)


# --- endpoint integration -------------------------------------------------


@pytest.fixture
def upload_dir(app):
    d = app.config["UPLOAD_FOLDER"]
    os.makedirs(d, exist_ok=True)
    yield d
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def _register(client):
    client.post(
        "/api/auth/register",
        json={"username": "m", "email": "m@e.com", "password": "secret123"},
    )


def _add(client, name, cost=100, qty=1):
    return client.post(
        "/api/products", json={"name": name, "cost_price": cost, "quantity": qty}
    ).get_json()["data"]


def _upload_photo(client, product_id, blob):
    return client.post(
        f"/api/products/{product_id}/photo",
        data={"photo": (io.BytesIO(blob), "p.png", "image/png")},
        content_type="multipart/form-data",
    )


@needs_mobileclip
def test_photo_upload_writes_embedding_to_db(client, upload_dir):
    _register(client)
    p = _add(client, "A")
    r = _upload_photo(client, p["id"], _png(color=(50, 100, 200)))
    assert r.status_code == 200

    from backend.models.product import Product
    from backend.database.db import db

    with client.application.app_context():
        row = db.session.get(Product, p["id"])
        assert row.photo_embedding is not None
        assert len(row.photo_embedding) == 512 * 4
        assert row.photo_embedded_at is not None


@needs_mobileclip
def test_identify_endpoint_uses_mobileclip_when_ready(client, upload_dir):
    _register(client)
    photo_a = _png(color=(50, 100, 200))
    photo_b = _png(color=(240, 240, 240))
    pa = _add(client, "Blue A")
    pb = _add(client, "White B")
    _upload_photo(client, pa["id"], photo_a)
    _upload_photo(client, pb["id"], photo_b)

    # Query with the exact photo of product A → similarity 1.0.
    r = client.post(
        "/api/ai/identify",
        data={"photo": (io.BytesIO(photo_a), "q.png", "image/png"), "mode": "single"},
        content_type="multipart/form-data",
    )
    d = r.get_json()["data"]
    assert d["method"] == "mobileclip"
    assert d["proposals"]
    top = d["proposals"][0]["candidates"][0]
    assert top["name"] == "Blue A"
    assert top["score"] == pytest.approx(1.0, abs=1e-3)
    assert "mobileclip_stats" in d


@needs_mobileclip
def test_identify_method_phash_forced(client, upload_dir):
    _register(client)
    p = _add(client, "A")
    _upload_photo(client, p["id"], _png(color=(50, 100, 200)))

    r = client.post(
        "/api/ai/identify",
        data={
            "photo": (io.BytesIO(_png(color=(50, 100, 200))), "q.png", "image/png"),
            "method": "phash",
        },
        content_type="multipart/form-data",
    )
    d = r.get_json()["data"]
    assert d["method"] == "phash"


@needs_mobileclip
def test_benchmark_includes_mobileclip_result(client, upload_dir):
    _register(client)
    p = _add(client, "Only one")
    _upload_photo(client, p["id"], _png(color=(50, 100, 200)))

    r = client.post(
        "/api/ai/vision-benchmark",
        data={"photo": (io.BytesIO(_png(color=(50, 100, 200))), "q.png", "image/png")},
        content_type="multipart/form-data",
    )
    body = r.get_json()
    assert body["success"] is True
    methods = {m["method"]: m for m in body["data"]["methods"]}
    assert "phash" in methods
    assert "mobileclip" in methods
    mc = methods["mobileclip"]
    assert mc.get("matches"), mc
    assert mc["matches"][0]["similarity"] == pytest.approx(1.0, abs=1e-3)


def test_benchmark_info_reports_embedding_count(auth_client):
    d = auth_client.get("/api/ai/vision-benchmark/info").get_json()["data"]
    assert "with_embedding" in d["catalog"]


def test_migration_adds_embedding_columns(tmp_path):
    """Old DB without photo_embedding column gets it added."""
    import sqlite3

    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE,
                password_hash TEXT
            );
            CREATE TABLE categories (id INTEGER PRIMARY KEY, user_id INT, name TEXT);
            CREATE TABLE products (
                id INTEGER PRIMARY KEY, user_id INT, name TEXT,
                cost_price NUMERIC, retail_price NUMERIC, quantity INT
            );
            INSERT INTO products (user_id, name, cost_price, retail_price, quantity)
              VALUES (1, 'Old', 100, 130, 5);
            """
        )

    from backend import create_app
    from backend.config import TestConfig

    class OldDbConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        DISABLE_MOBILECLIP_WARMUP = True

    app = create_app(OldDbConfig)
    with app.app_context():
        with sqlite3.connect(db_path) as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(products)")]
            assert "photo_embedding" in cols
            assert "photo_embedded_at" in cols
