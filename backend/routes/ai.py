import os
import time
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from ..database.db import db
from ..models.product import Product
from ..services import mobileclip
from ..services.llm import StubLLM, get_llm, get_vision_llm
from ..services.nl_to_sql import answer_question
from ..services.photo_match import identify_from_photo
from ..services.vision_local import (
    Candidate,
    phash,
    phash_hex,
    rank_phash,
)

bp = Blueprint("ai", __name__)


ALLOWED_PHOTO_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
}


def _sqlite_path_from_uri(uri: str) -> str:
    prefix = "sqlite:///"
    if not uri.startswith(prefix):
        return ""
    return uri[len(prefix):]


@bp.get("/status")
@login_required
def status():
    provider = (current_app.config.get("LLM_PROVIDER") or "stub").lower()
    key_present = bool(current_app.config.get("LLM_API_KEY"))
    vision_key_present = bool(
        current_app.config.get("VISION_API_KEY") or current_app.config.get("LLM_API_KEY")
    )
    stub_mode = provider == "stub"
    return jsonify(
        {
            "success": True,
            "data": {
                "provider": provider,
                "text_model": current_app.config.get("LLM_MODEL"),
                "vision_model": current_app.config.get("VISION_MODEL"),
                "base_url": current_app.config.get("LLM_BASE_URL"),
                "key_present": key_present,
                "vision_key_present": vision_key_present,
                "stub_mode": stub_mode,
                "example_questions": [
                    "How much profit did I make today?",
                    "What's my best-selling product?",
                    "Which items are low stock?",
                    "How much did I make this month?",
                    "How many products do I have?",
                ],
            },
        }
    )


@bp.post("/chat")
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"success": False, "error": "question is required"}), 400

    db_path = _sqlite_path_from_uri(current_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if not db_path or db_path == ":memory:":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "AI chat requires a file-backed SQLite database.",
                }
            ),
            400,
        )

    llm = get_llm(current_app.config)
    result = answer_question(
        question=question,
        user_id=current_user.id,
        db_path=db_path,
        llm=llm,
        max_rows=current_app.config.get("SQL_MAX_ROWS", 100),
        timeout_ms=current_app.config.get("SQL_TIMEOUT_MS", 3000),
    )
    return jsonify({"success": True, "data": result.to_dict()})


@bp.post("/identify")
@login_required
def identify():
    """Photo → catalog match. Uses local pHash against product photos when
    no LLM is configured (default). Falls back to vision-LLM identification
    when LLM_PROVIDER is set to a real provider.
    """
    file = request.files.get("photo") or request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"success": False, "error": "No photo uploaded (field: photo)"}), 400

    mime = (file.mimetype or "").lower()
    if mime not in ALLOWED_PHOTO_MIMES:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Unsupported image type: {mime or 'unknown'}",
                }
            ),
            400,
        )

    photo_bytes = file.read()
    if not photo_bytes:
        return jsonify({"success": False, "error": "Empty photo"}), 400
    if len(photo_bytes) > current_app.config.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024):
        return jsonify({"success": False, "error": "Photo too large"}), 400

    mode = (request.form.get("mode") or "multi").lower()
    if mode not in {"multi", "single"}:
        mode = "multi"

    catalog = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(Product.quantity > 0)
        .all()
    )
    if not catalog:
        return jsonify(
            {
                "success": True,
                "data": {
                    "proposals": [],
                    "error": "You have no in-stock products to match against.",
                    "used_stub": False,
                    "mode": mode,
                    "method": "none",
                },
            }
        )

    # Method preference:
    #   1. MobileCLIP (semantic embeddings) if the model is ready.
    #   2. pHash (fast, brittle) as fallback.
    #   3. Real vision-LLM only when explicitly configured (LLM_PROVIDER != stub).
    requested = (request.form.get("method") or "").lower()
    provider = (current_app.config.get("LLM_PROVIDER") or "stub").lower()

    if provider != "stub" and requested != "phash" and requested != "mobileclip":
        # User configured a real LLM — use it.
        llm = get_vision_llm(current_app.config)
        result = identify_from_photo(
            photo_bytes=photo_bytes,
            mime_type=mime if mime != "image/jpg" else "image/jpeg",
            catalog=catalog,
            llm=llm,
            mode=mode,
            auto_pick_threshold=float(
                current_app.config.get("IDENTIFY_AUTO_PICK_CONFIDENCE", 0.85)
            ),
            max_items=int(current_app.config.get("IDENTIFY_MAX_ITEMS", 8)),
            max_candidates=int(current_app.config.get("IDENTIFY_MAX_CANDIDATES", 3)),
            used_stub=isinstance(llm, StubLLM),
        )
        payload = result.to_dict()
        payload["mode"] = mode
        payload["method"] = "llm-vision"
        return jsonify({"success": True, "data": payload})

    if requested == "phash":
        return _identify_via_phash(photo_bytes, mode, catalog)

    # Default local path: MobileCLIP if ready, pHash otherwise.
    if mobileclip.is_ready() or mobileclip.ensure_ready():
        return _identify_via_mobileclip(photo_bytes, mode, catalog)

    # Model not ready yet (still downloading). Fall back to pHash so the
    # request doesn't hang for 30+ seconds, and let the client know why.
    resp = _identify_via_phash(photo_bytes, mode, catalog)
    body = resp.get_json()
    if body and body.get("success"):
        body["data"]["mobileclip_status"] = mobileclip.status().to_dict()
    return jsonify(body), resp.status_code


def _identify_via_mobileclip(photo_bytes, mode, catalog):
    """Embed the query photo, compare to cached catalog embeddings.

    Products with a photo but no cached embedding get backfilled here. That's
    a one-off cost per product per photo, ~40 ms on CPU.
    """
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    max_candidates = int(current_app.config.get("IDENTIFY_MAX_CANDIDATES", 3))
    auto_pick_threshold = float(
        current_app.config.get("IDENTIFY_AUTO_PICK_CONFIDENCE", 0.85)
    )

    t0 = time.perf_counter()
    try:
        query_emb = mobileclip.embed(photo_bytes)
    except Exception as e:
        current_app.logger.exception("MobileCLIP embed failed on query photo")
        # Fall back to pHash — better than showing an error.
        resp = _identify_via_phash(photo_bytes, mode, catalog)
        body = resp.get_json()
        if body and body.get("success"):
            body["data"]["fallback_from"] = "mobileclip"
            body["data"]["fallback_reason"] = str(e)
        return jsonify(body), resp.status_code
    query_ms = (time.perf_counter() - t0) * 1000

    # Build (product, embedding) pairs, backfilling missing embeddings on
    # the fly so this also serves as the migration path for products whose
    # photos predate MobileCLIP being wired up.
    pairs = []
    backfilled = 0
    for p in catalog:
        if not p.photo_url or not p.photo_url.startswith("/uploads/"):
            continue
        emb = p.photo_embedding
        if emb is not None:
            try:
                pairs.append((p, mobileclip.from_bytes(emb)))
                continue
            except Exception:
                # Corrupted cache — recompute.
                pass

        path = os.path.join(upload_dir, os.path.basename(p.photo_url))
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                vec = mobileclip.embed(f.read())
            p.photo_embedding = mobileclip.to_bytes(vec)
            p.photo_embedded_at = datetime.utcnow()
            backfilled += 1
            pairs.append((p, vec))
        except Exception as e:
            current_app.logger.warning("MobileCLIP embed failed for product %s: %s", p.id, e)
            continue

    if backfilled:
        db.session.commit()

    if not pairs:
        return jsonify(
            {
                "success": True,
                "data": {
                    "proposals": [],
                    "error": (
                        "None of your in-stock products have photos yet. "
                        "Add a photo to a few products first so I have something to match against."
                    ),
                    "used_stub": False,
                    "mode": mode,
                    "method": "mobileclip",
                },
            }
        )

    t1 = time.perf_counter()
    ranked = mobileclip.rank(query_emb, [(p.id, e) for p, e in pairs], top_n=max_candidates)
    compare_ms = (time.perf_counter() - t1) * 1000

    prod_by_id = {p.id: p for p, _ in pairs}
    frontend_candidates = []
    for m in ranked:
        p = prod_by_id[m.product_id]
        frontend_candidates.append(
            {
                "product_id": p.id,
                "unique_id": p.unique_id or "",
                "name": p.name,
                "photo_url": p.photo_url,
                "retail_price": float(p.retail_price),
                "quantity": p.quantity,
                "unit": (p.category.unit if p.category else None) or "pieces",
                "category_name": p.category.name if p.category else None,
                "score": round(m.similarity, 3),
            }
        )

    top_similarity = frontend_candidates[0]["score"] if frontend_candidates else 0.0
    auto_pick = top_similarity >= auto_pick_threshold

    proposal = {
        "description": "Item in photo",
        "quantity": 1,
        "confidence": round(top_similarity, 3),
        "auto_pick": auto_pick,
        "candidates": frontend_candidates,
    }

    return jsonify(
        {
            "success": True,
            "data": {
                "proposals": [proposal],
                "error": None,
                "used_stub": False,
                "mode": mode,
                "method": "mobileclip",
                "mobileclip_stats": {
                    "candidates_scanned": len(pairs),
                    "query_ms": round(query_ms, 2),
                    "compare_ms": round(compare_ms, 2),
                    "top_similarity": round(top_similarity, 3),
                    "backfilled": backfilled,
                },
            },
        }
    )


def _identify_via_phash(photo_bytes, mode, catalog):
    """Rank the counter photo against every catalog product photo using
    local perceptual hashing. Returns proposals in the same shape as the
    LLM path so the frontend doesn't care which method was used.

    Modelled as ONE proposal with the top-3 catalog matches as candidates.
    In single-item mode this is exactly what you want (owner picks the
    right product). In multi mode we still return a single proposal — the
    owner can 'Snap one more item' to add more.
    """
    upload_dir = current_app.config["UPLOAD_FOLDER"]

    # Build (Candidate, product) pairs; skip products whose photo file is
    # missing on disk.
    pairs = []
    for p in catalog:
        if not p.photo_url or not p.photo_url.startswith("/uploads/"):
            continue
        path = os.path.join(upload_dir, os.path.basename(p.photo_url))
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                h = phash(f.read())
        except Exception as e:
            current_app.logger.warning(
                "phash failed for product %s (%s): %s", p.id, path, e
            )
            continue
        pairs.append(
            (
                p,
                Candidate(
                    id=p.id,
                    label=p.name,
                    photo_url=p.photo_url,
                    phash=h,
                    extra={},
                ),
            )
        )

    if not pairs:
        return jsonify(
            {
                "success": True,
                "data": {
                    "proposals": [],
                    "error": (
                        "None of your in-stock products have photos yet. "
                        "Add a photo to a few products first so I have something to match against."
                    ),
                    "used_stub": False,
                    "mode": mode,
                    "method": "phash",
                },
            }
        )

    max_candidates = int(current_app.config.get("IDENTIFY_MAX_CANDIDATES", 3))
    auto_pick_threshold = float(
        current_app.config.get("IDENTIFY_AUTO_PICK_CONFIDENCE", 0.85)
    )

    t0 = time.perf_counter()
    ranked = rank_phash(photo_bytes, [c for _, c in pairs], top_n=max_candidates)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Convert RankedMatch → the "candidate" shape the frontend expects.
    prod_by_id = {p.id: p for p, _ in pairs}
    frontend_candidates = []
    for m in ranked.matches:
        p = prod_by_id[m.id]
        frontend_candidates.append(
            {
                "product_id": p.id,
                "unique_id": p.unique_id or "",
                "name": p.name,
                "photo_url": p.photo_url,
                "retail_price": float(p.retail_price),
                "quantity": p.quantity,
                "unit": (p.category.unit if p.category else None) or "pieces",
                "category_name": p.category.name if p.category else None,
                "score": round(m.similarity, 3),
                "hamming": m.hamming,
            }
        )

    top_similarity = frontend_candidates[0]["score"] if frontend_candidates else 0.0
    auto_pick = top_similarity >= auto_pick_threshold

    proposal = {
        "description": "Item in photo",
        "quantity": 1,
        "confidence": round(top_similarity, 3),
        "auto_pick": auto_pick,
        "candidates": frontend_candidates,
    }

    return jsonify(
        {
            "success": True,
            "data": {
                "proposals": [proposal],
                "error": None,
                "used_stub": False,
                "mode": mode,
                "method": "phash",
                "phash_stats": {
                    "candidates_scanned": len(pairs),
                    "total_ms": round(elapsed_ms, 2),
                    "top_similarity": round(top_similarity, 3),
                    "top_hamming": frontend_candidates[0]["hamming"]
                    if frontend_candidates
                    else None,
                },
            },
        }
    )


@bp.get("/vision-benchmark/info")
@login_required
def vision_benchmark_info():
    """List what the benchmark can compare, and the size of the candidate set."""
    with_photo = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(Product.photo_url.isnot(None))
        .count()
    )
    with_embedding = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(Product.photo_embedding.isnot(None))
        .count()
    )
    total = Product.query.filter_by(user_id=current_user.id).count()
    mc_status = mobileclip.status()
    return jsonify(
        {
            "success": True,
            "data": {
                "methods": [
                    {
                        "id": "phash",
                        "name": "Perceptual hash (pHash)",
                        "description": "64-bit DCT hash. Zero ML deps. Fast; brittle to angle/lighting changes.",
                        "available": True,
                    },
                    {
                        "id": "mobileclip",
                        "name": "MobileCLIP-S0 (semantic)",
                        "description": "512-dim semantic embeddings via ONNX. ~43 MB model, ~40 ms per photo on CPU. Robust to angle/lighting.",
                        "available": mc_status.ready,
                        "loading": mc_status.loading,
                        "error": mc_status.error,
                    },
                ],
                "catalog": {
                    "total_products": total,
                    "with_photo": with_photo,
                    "with_embedding": with_embedding,
                    "missing_photo": total - with_photo,
                },
            },
        }
    )


@bp.post("/vision-benchmark")
@login_required
def vision_benchmark():
    """Given a query photo, rank the user's catalog against it using each
    available method and report timings. This is a research/UX endpoint —
    NOT part of the billing flow. Once we pick a method, we hard-wire it.
    """
    file = request.files.get("photo") or request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"success": False, "error": "No photo uploaded"}), 400
    mime = (file.mimetype or "").lower()
    if mime not in ALLOWED_PHOTO_MIMES:
        return jsonify({"success": False, "error": f"Unsupported image type: {mime}"}), 400

    query_bytes = file.read()
    if not query_bytes:
        return jsonify({"success": False, "error": "Empty photo"}), 400

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    products = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(Product.photo_url.isnot(None))
        .all()
    )
    if not products:
        return jsonify(
            {
                "success": True,
                "data": {
                    "error": "You have no products with photos yet — add photos to at least a few products first.",
                    "methods": [],
                },
            }
        )

    # Build candidates. On errors reading a file, skip it silently.
    candidates: list[Candidate] = []
    hash_build_ms = 0.0
    t0 = time.perf_counter()
    for p in products:
        if not p.photo_url or not p.photo_url.startswith("/uploads/"):
            continue
        path = os.path.join(upload_dir, os.path.basename(p.photo_url))
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                data = f.read()
            h = phash(data)
        except Exception:
            continue
        candidates.append(
            Candidate(
                id=p.id,
                label=p.name,
                photo_url=p.photo_url,
                phash=h,
                extra={
                    "unique_id": p.unique_id or "",
                    "phash_hex": phash_hex(h),
                    "quantity": p.quantity,
                    "retail_price": float(p.retail_price),
                    "category_name": p.category.name if p.category else None,
                },
            )
        )
    hash_build_ms = (time.perf_counter() - t0) * 1000

    top_n = int(request.form.get("top_n", 10))
    top_n = max(1, min(50, top_n))

    results = []

    # pHash
    phash_result = rank_phash(query_bytes, candidates, top_n=top_n)
    d = phash_result.to_dict()
    d["catalog_hash_build_ms"] = round(hash_build_ms, 3)
    results.append(d)

    # MobileCLIP
    if mobileclip.is_ready() or mobileclip.ensure_ready():
        try:
            t0 = time.perf_counter()
            query_emb = mobileclip.embed(query_bytes)
            query_ms = (time.perf_counter() - t0) * 1000

            # Build (product, embedding) pairs, backfilling as needed.
            t1 = time.perf_counter()
            emb_pairs = []
            backfilled = 0
            for p in products:
                if not p.photo_url or not p.photo_url.startswith("/uploads/"):
                    continue
                emb = p.photo_embedding
                if emb is not None:
                    try:
                        emb_pairs.append((p, mobileclip.from_bytes(emb)))
                        continue
                    except Exception:
                        pass
                path = os.path.join(upload_dir, os.path.basename(p.photo_url))
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "rb") as f:
                        vec = mobileclip.embed(f.read())
                    p.photo_embedding = mobileclip.to_bytes(vec)
                    p.photo_embedded_at = datetime.utcnow()
                    backfilled += 1
                    emb_pairs.append((p, vec))
                except Exception:
                    continue
            if backfilled:
                db.session.commit()
            catalog_hash_build_ms = (time.perf_counter() - t1) * 1000

            t2 = time.perf_counter()
            ranked = mobileclip.rank(
                query_emb, [(p.id, e) for p, e in emb_pairs], top_n=top_n
            )
            compare_ms = (time.perf_counter() - t2) * 1000

            prod_by_id = {p.id: p for p, _ in emb_pairs}
            matches = []
            for m in ranked:
                p = prod_by_id[m.product_id]
                matches.append(
                    {
                        "id": p.id,
                        "label": p.name,
                        "photo_url": p.photo_url,
                        "similarity": round(m.similarity, 4),
                        "unique_id": p.unique_id or "",
                        "quantity": p.quantity,
                        "retail_price": float(p.retail_price),
                        "category_name": p.category.name if p.category else None,
                    }
                )
            results.append(
                {
                    "method": "mobileclip",
                    "query_ms": round(query_ms, 3),
                    "compare_ms": round(compare_ms, 3),
                    "total_ms": round(query_ms + compare_ms, 3),
                    "catalog_hash_build_ms": round(catalog_hash_build_ms, 3),
                    "candidate_count": len(emb_pairs),
                    "backfilled": backfilled,
                    "matches": matches,
                }
            )
        except Exception as e:
            current_app.logger.exception("MobileCLIP benchmark failed")
            results.append(
                {
                    "method": "mobileclip",
                    "note": f"MobileCLIP inference failed: {e}",
                    "matches": [],
                }
            )
    else:
        status = mobileclip.status()
        note = (
            f"downloading model — {int(status.seconds_since_load_started or 0)}s so far"
            if status.loading
            else (status.error or "not ready yet")
        )
        results.append({"method": "mobileclip", "note": note, "matches": []})

    return jsonify(
        {
            "success": True,
            "data": {
                "methods": results,
                "candidate_count": len(candidates),
                "skipped_no_photo": len(products) - len(candidates),
            },
        }
    )
