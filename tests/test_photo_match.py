"""Tests for the photo → items → catalog matching pipeline.

We hit the matcher directly with fabricated Product-like objects for the
scoring tests, and hit the real POST /api/ai/identify endpoint using the
stub vision LLM for end-to-end coverage.
"""

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from backend.services.photo_match import (
    _extract_json_array,
    _tokenize,
    match_catalog,
    identify_from_photo,
)
from backend.services.llm import StubLLM


TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63f8cf000000030001010060fabc0000000049454e"
    "44ae426082"
)


def _real_png(color=(50, 100, 200), size=(64, 64)) -> bytes:
    """A properly-formed PNG suitable for pHash. The 1×1 TINY_PNG above is
    fine for upload-endpoint tests but crashes PIL's bilinear resize."""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --- helpers ---------------------------------------------------------------


def _mkp(id, name, category_name=None, unit="pieces", retail=100, quantity=5, desc=None):
    """Duck-typed Product for matcher unit tests."""
    cat = SimpleNamespace(name=category_name, unit=unit) if category_name else None
    return SimpleNamespace(
        id=id,
        unique_id=f"INSTOX-{id:05d}",
        name=name,
        description=desc,
        retail_price=retail,
        quantity=quantity,
        photo_url=None,
        category=cat,
    )


# --- tokenizer -------------------------------------------------------------


def test_tokenize_strips_stopwords():
    assert _tokenize("A blue cotton curtain") == ["blue", "cotton", "curtain"]


def test_tokenize_handles_none_and_empty():
    assert _tokenize("") == []
    assert _tokenize(None) == []


# --- JSON extraction -------------------------------------------------------


def test_extract_json_array_bare():
    assert _extract_json_array('[{"a": 1}]') == [{"a": 1}]


def test_extract_json_array_fenced():
    assert _extract_json_array('Here it is:\n```json\n[{"a": 1}]\n```\n') == [{"a": 1}]


def test_extract_json_array_with_prose():
    assert _extract_json_array('Sure! [{"a": 1}] all done.') == [{"a": 1}]


def test_extract_json_array_returns_none_when_missing():
    assert _extract_json_array("no json here") is None
    assert _extract_json_array("") is None


# --- matcher scoring -------------------------------------------------------


def test_matcher_ranks_by_name_overlap():
    catalog = [
        _mkp(1, "Blue Cotton Curtain 6x8", category_name="Curtains"),
        _mkp(2, "White Bed Sheet", category_name="Home Textiles"),
        _mkp(3, "Red Silk Saree", category_name="Sarees"),
    ]
    matches = match_catalog("blue curtain", None, catalog)
    assert matches[0].name == "Blue Cotton Curtain 6x8"


def test_matcher_uses_category_hint_bonus():
    curtain_cat = "Curtains"
    catalog = [
        _mkp(1, "Blue Fabric", category_name="Fabrics"),
        _mkp(2, "Cotton Piece", category_name=curtain_cat),
    ]
    # description alone is ambiguous, hint tips it toward Curtains
    matches = match_catalog("cotton piece", "curtains", catalog)
    assert matches[0].name == "Cotton Piece"


def test_matcher_returns_top_n():
    catalog = [_mkp(i, f"Curtain {i}", category_name="Curtains") for i in range(1, 11)]
    matches = match_catalog("curtain", None, catalog, top_n=3)
    assert len(matches) == 3


def test_matcher_returns_empty_when_no_overlap():
    catalog = [_mkp(1, "Blue Curtain", category_name="Curtains")]
    matches = match_catalog("chair", None, catalog)
    assert matches == []


# --- full pipeline (stub vision) -------------------------------------------


def test_identify_end_to_end_with_stub_returns_proposals():
    catalog = [
        _mkp(1, "Blue Cotton Curtain 6x8", category_name="Curtains"),
        _mkp(2, "White Bed Sheet", category_name="Home Textiles"),
        _mkp(3, "Red Saree", category_name="Sarees"),
    ]
    result = identify_from_photo(
        photo_bytes=TINY_PNG,
        mime_type="image/png",
        catalog=catalog,
        llm=StubLLM(),
        mode="multi",
        used_stub=True,
    )
    assert result.error is None
    # Stub returns [blue curtain qty=2, white bedsheet qty=1]
    assert len(result.proposals) == 2
    props = {p.description: p for p in result.proposals}
    assert "blue curtain" in props
    assert props["blue curtain"].candidates
    assert props["blue curtain"].candidates[0].name == "Blue Cotton Curtain 6x8"
    assert props["white bedsheet"].candidates[0].name == "White Bed Sheet"


def test_identify_single_mode_returns_one_proposal():
    catalog = [_mkp(1, "Anything", category_name="Other")]
    result = identify_from_photo(
        photo_bytes=TINY_PNG,
        mime_type="image/png",
        catalog=catalog,
        llm=StubLLM(),
        mode="single",
        used_stub=True,
    )
    assert result.error is None
    assert len(result.proposals) == 1


def test_identify_marks_auto_pick_when_clear_winner():
    """Vision confidence 0.9 + only one strong match → should auto-pick."""
    catalog = [
        _mkp(1, "Blue Curtain", category_name="Curtains"),
        _mkp(2, "Wooden Chair", category_name="Other"),
    ]
    result = identify_from_photo(
        photo_bytes=TINY_PNG,
        mime_type="image/png",
        catalog=catalog,
        llm=StubLLM(),
        mode="multi",
        used_stub=True,
        auto_pick_threshold=0.6,  # relaxed so the stub triggers it
    )
    # "blue curtain" → clear match against "Blue Curtain"
    blue = next(p for p in result.proposals if "curtain" in p.description)
    assert blue.auto_pick is True


# --- HTTP endpoint ---------------------------------------------------------


def _register_and_add(client, products):
    client.post(
        "/api/auth/register",
        json={"username": "n", "email": "n@e.com", "password": "secret123"},
    )
    for name, qty, cat in products:
        # Find the seeded category id
        cats = client.get("/api/categories").get_json()["data"]
        cat_id = next((c["id"] for c in cats if c["name"] == cat), None)
        client.post(
            "/api/products",
            json={"name": name, "cost_price": 100, "quantity": qty, "category_id": cat_id},
        )


def test_identify_endpoint_requires_photo(auth_client):
    res = auth_client.post("/api/ai/identify", data={})
    assert res.status_code == 400


def test_identify_endpoint_rejects_bad_mime(auth_client):
    res = auth_client.post(
        "/api/ai/identify",
        data={"photo": (io.BytesIO(b"pdf"), "x.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400


def test_identify_endpoint_empty_catalog(client):
    client.post(
        "/api/auth/register",
        json={"username": "n2", "email": "n2@e.com", "password": "secret123"},
    )
    res = client.post(
        "/api/ai/identify",
        data={"photo": (io.BytesIO(TINY_PNG), "s.png", "image/png")},
        content_type="multipart/form-data",
    )
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["proposals"] == []
    assert "no in-stock" in body["data"]["error"]


def test_identify_endpoint_returns_pHash_matches_when_products_have_photos(client):
    """In stub mode the endpoint routes to local pHash. Products need photos
    on disk to be matched against."""
    _register_and_add(
        client,
        [
            ("Blue Cotton Curtain", 10, "Curtains"),
            ("White Bed Sheet", 5, "Home Textiles"),
        ],
    )
    photo_a = _real_png(color=(50, 100, 200))
    photo_b = _real_png(color=(240, 240, 240))
    for pid, blob in [(1, photo_a), (2, photo_b)]:
        client.post(
            f"/api/products/{pid}/photo",
            data={"photo": (io.BytesIO(blob), f"p{pid}.png", "image/png")},
            content_type="multipart/form-data",
        )

    # Query with the same image as product 1 → top match should be an exact hit.
    # Force pHash method so this test doesn't need MobileCLIP.
    res = client.post(
        "/api/ai/identify",
        data={
            "photo": (io.BytesIO(photo_a), "s.png", "image/png"),
            "mode": "multi",
            "method": "phash",
        },
        content_type="multipart/form-data",
    )
    body = res.get_json()
    assert body["success"] is True, body
    d = body["data"]
    assert d["method"] == "phash"
    assert d["used_stub"] is False
    assert len(d["proposals"]) == 1
    assert len(d["proposals"][0]["candidates"]) >= 1
    top = d["proposals"][0]["candidates"][0]
    assert top["name"] == "Blue Cotton Curtain"
    assert top["score"] == 1.0
    assert top["hamming"] == 0
    assert d["phash_stats"]["candidates_scanned"] == 2


def test_identify_endpoint_reports_error_when_no_products_have_photos(client):
    _register_and_add(client, [("Just One Thing", 5, "Other")])
    res = client.post(
        "/api/ai/identify",
        data={
            "photo": (io.BytesIO(_real_png()), "s.png", "image/png"),
            "mode": "single",
            "method": "phash",
        },
        content_type="multipart/form-data",
    )
    d = res.get_json()["data"]
    assert d["method"] == "phash"
    assert d["proposals"] == []
    assert "photo" in d["error"].lower()
