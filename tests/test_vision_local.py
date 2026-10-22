"""Tests for pHash + vision-benchmark endpoint."""

import io
import os
import shutil

import pytest
from PIL import Image

from backend.services.vision_local import (
    Candidate,
    hamming,
    is_mobileclip_available,
    phash,
    phash_from_hex,
    phash_hex,
    rank_phash,
    similarity,
)


def _make_png(color=(0, 0, 0), size=(64, 64)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_gradient(size=(64, 64), horizontal=True) -> bytes:
    img = Image.new("L", size, 0)
    for y in range(size[1]):
        for x in range(size[0]):
            v = int(255 * (x if horizontal else y) / (size[0] - 1))
            img.putpixel((x, y), v)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


# --- basic hash properties -------------------------------------------------


def test_phash_is_stable_for_same_bytes():
    b = _make_gradient()
    assert phash(b) == phash(b)


def test_phash_hex_roundtrip():
    b = _make_gradient()
    h = phash(b)
    assert phash_from_hex(phash_hex(h)) == h
    assert len(phash_hex(h)) == 16


def test_similarity_and_hamming_bounds():
    b1 = _make_gradient(horizontal=True)
    b2 = _make_gradient(horizontal=True)
    b3 = _make_gradient(horizontal=False)

    h1, h2, h3 = phash(b1), phash(b2), phash(b3)
    assert hamming(h1, h2) == 0
    assert similarity(h1, h2) == 1.0
    # Very different structure → measurably different hash. We allow a wide
    # band because different image contents can still share median-side bits.
    assert hamming(h1, h3) >= 8
    assert 0.0 <= similarity(h1, h3) <= 1.0


def test_phash_similar_photos_are_closer_than_dissimilar():
    """Two versions of the same image (slight brightness shift) should be
    closer than two structurally different images."""
    base = Image.new("L", (128, 128), 0)
    for y in range(128):
        for x in range(128):
            base.putpixel((x, y), (x + y) % 256)
    a_buf = io.BytesIO()
    base.convert("RGB").save(a_buf, format="PNG")

    # Slightly brighter version — same structure
    brighter = Image.eval(base, lambda v: min(255, v + 20))
    b_buf = io.BytesIO()
    brighter.convert("RGB").save(b_buf, format="PNG")

    # A totally different image
    diff = Image.new("L", (128, 128), 128)
    for y in range(128):
        for x in range(128):
            diff.putpixel((x, y), (x * 3 - y * 5) % 256)
    c_buf = io.BytesIO()
    diff.convert("RGB").save(c_buf, format="PNG")

    d_similar = hamming(phash(a_buf.getvalue()), phash(b_buf.getvalue()))
    d_different = hamming(phash(a_buf.getvalue()), phash(c_buf.getvalue()))
    assert d_similar < d_different


# --- ranking ---------------------------------------------------------------


def test_rank_phash_puts_exact_match_first():
    photos = {
        1: _make_gradient(horizontal=True),
        2: _make_gradient(horizontal=False),
        3: _make_png(color=(200, 30, 30)),
    }
    candidates = [
        Candidate(id=k, label=f"p{k}", photo_url=None, phash=phash(v), extra={})
        for k, v in photos.items()
    ]
    # Query the horizontal-gradient exactly → should top the ranking.
    result = rank_phash(photos[1], candidates, top_n=3)
    assert result.matches[0].id == 1
    assert result.matches[0].hamming == 0
    assert result.matches[0].similarity == 1.0
    assert result.method == "phash"
    assert result.candidate_count == 3
    assert result.query_ms > 0
    assert result.compare_ms >= 0


def test_rank_phash_respects_top_n():
    q = _make_gradient()
    candidates = [
        Candidate(id=i, label=f"p{i}", photo_url=None, phash=phash(_make_gradient()), extra={})
        for i in range(20)
    ]
    result = rank_phash(q, candidates, top_n=5)
    assert len(result.matches) == 5


# --- MobileCLIP is stubbed out honestly ------------------------------------


def test_mobileclip_availability_is_reported_honestly():
    # Whether onnxruntime is installed or not, the function must return bool.
    assert isinstance(is_mobileclip_available(), bool)


# --- vision-benchmark endpoint --------------------------------------------


@pytest.fixture
def upload_dir(app):
    d = app.config["UPLOAD_FOLDER"]
    os.makedirs(d, exist_ok=True)
    yield d
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def _register_with_products_and_photos(client, upload_dir, seed_photos):
    client.post(
        "/api/auth/register",
        json={"username": "v", "email": "v@e.com", "password": "secret123"},
    )
    ids = []
    for name, photo_bytes in seed_photos:
        p = client.post(
            "/api/products", json={"name": name, "cost_price": 10, "quantity": 1}
        ).get_json()["data"]
        ids.append(p["id"])
        r = client.post(
            f"/api/products/{p['id']}/photo",
            data={"photo": (io.BytesIO(photo_bytes), f"{name}.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 200, r.get_json()
    return ids


def test_benchmark_info_reports_catalog_state(auth_client):
    r = auth_client.get("/api/ai/vision-benchmark/info")
    assert r.status_code == 200
    d = r.get_json()["data"]
    method_ids = {m["id"] for m in d["methods"]}
    assert "phash" in method_ids
    assert "mobileclip" in method_ids


def test_benchmark_returns_error_when_no_photos(auth_client):
    q = _make_gradient()
    r = auth_client.post(
        "/api/ai/vision-benchmark",
        data={"photo": (io.BytesIO(q), "q.png", "image/png")},
        content_type="multipart/form-data",
    )
    body = r.get_json()
    assert body["success"] is True
    assert "no products with photos" in body["data"]["error"]


def test_benchmark_ranks_exact_match_first(client, upload_dir):
    h_gradient = _make_gradient(horizontal=True)
    v_gradient = _make_gradient(horizontal=False)
    solid_red = _make_png(color=(200, 20, 20))

    _register_with_products_and_photos(
        client,
        upload_dir,
        [("Horizontal", h_gradient), ("Vertical", v_gradient), ("Red", solid_red)],
    )

    r = client.post(
        "/api/ai/vision-benchmark",
        data={"photo": (io.BytesIO(h_gradient), "query.png", "image/png")},
        content_type="multipart/form-data",
    )
    body = r.get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["candidate_count"] == 3
    phash_method = next(m for m in data["methods"] if m["method"] == "phash")
    assert phash_method["matches"][0]["label"] == "Horizontal"
    assert phash_method["matches"][0]["similarity"] == 1.0
    assert phash_method["query_ms"] > 0


def test_benchmark_rejects_bad_mime(auth_client, upload_dir):
    r = auth_client.post(
        "/api/ai/vision-benchmark",
        data={"photo": (io.BytesIO(b"pdf"), "q.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400


def test_benchmark_requires_file(auth_client):
    r = auth_client.post("/api/ai/vision-benchmark", data={})
    assert r.status_code == 400


def test_vision_test_html_served(client):
    r = client.get("/vision_test.html")
    assert r.status_code == 200
    assert b"Vision matching benchmark" in r.data


def test_phash_js_served(client):
    r = client.get("/static/js/phash.js")
    assert r.status_code == 200
    assert b"InstoxPhash" in r.data
