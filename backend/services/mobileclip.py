"""MobileCLIP-S0 image embeddings via ONNX Runtime.

Model: Xenova/mobileclip_s0 (vision_model.onnx, ~43 MB fp32).
On first use we download from HuggingFace and cache to ~/.cache/huggingface/hub.
Subsequent runs load from cache instantly.

Preprocessing (from the model's preprocessor_config.json):
  1. Convert to RGB.
  2. Resize with bilinear so shortest edge == 256 (aspect ratio preserved).
  3. Center crop to 256×256.
  4. Rescale to [0, 1] (divide by 255). NO mean/std normalization.
  5. Reshape to (1, 3, 256, 256), channel-first.

Output: 512-dim float32 vector. We L2-normalize for cosine similarity.

Threading: the ONNX session is lazily loaded at first use and cached at module
level. Access is protected by a lock so multiple concurrent requests don't
duplicate the download.
"""

from __future__ import annotations

import io
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

MODEL_REPO = "Xenova/mobileclip_s0"
MODEL_FILE = "onnx/vision_model.onnx"
EMBEDDING_DIM = 512
IMAGE_SIZE = 256


# ---------------------------------------------------------------------------
# Session cache (lazy, thread-safe)
# ---------------------------------------------------------------------------


_load_lock = threading.Lock()
_session: Optional[object] = None  # onnxruntime.InferenceSession
_input_name: Optional[str] = None
_load_error: Optional[str] = None
_download_started_at: Optional[float] = None
_ready = False


def _ensure_session_locked():
    """Load the ONNX session. Caller must hold `_load_lock`."""
    global _session, _input_name, _load_error, _ready, _download_started_at

    if _session is not None or _load_error is not None:
        return

    _download_started_at = time.time()
    try:
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        _load_error = f"onnxruntime / huggingface_hub missing: {e}"
        return

    try:
        # hf_hub_download caches to ~/.cache/huggingface/hub. First call
        # downloads ~43 MB; subsequent calls return the cached path instantly.
        model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
        session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        _session = session
        _input_name = session.get_inputs()[0].name
        _ready = True
    except Exception as e:
        _load_error = f"failed to load MobileCLIP: {e}"


def ensure_ready() -> bool:
    """Try to load the model. Returns True on success, False otherwise.

    Safe to call from anywhere; idempotent."""
    with _load_lock:
        _ensure_session_locked()
    return _session is not None and _load_error is None


def warmup_async():
    """Fire-and-forget: kick model load off to a background thread on server
    startup so the first real request doesn't pay the download cost."""
    t = threading.Thread(target=ensure_ready, name="mobileclip-warmup", daemon=True)
    t.start()


@dataclass
class Status:
    ready: bool
    loading: bool
    error: Optional[str]
    embedding_dim: int
    image_size: int
    seconds_since_load_started: Optional[float]

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "loading": self.loading,
            "error": self.error,
            "embedding_dim": self.embedding_dim,
            "image_size": self.image_size,
            "seconds_since_load_started": self.seconds_since_load_started,
        }


def status() -> Status:
    with _load_lock:
        # Are we currently downloading? If someone kicked off the warmup and it
        # hasn't finished, session is None but error is None.
        loading = _session is None and _load_error is None and _download_started_at is not None
        elapsed = time.time() - _download_started_at if _download_started_at else None
        return Status(
            ready=_session is not None and _load_error is None,
            loading=loading,
            error=_load_error,
            embedding_dim=EMBEDDING_DIM,
            image_size=IMAGE_SIZE,
            seconds_since_load_started=elapsed,
        )


def is_ready() -> bool:
    with _load_lock:
        return _session is not None and _load_error is None


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------


def _preprocess(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Resize so shortest edge = 256, aspect ratio preserved.
    w, h = img.size
    if w < h:
        new_w = IMAGE_SIZE
        new_h = int(round(h * IMAGE_SIZE / w))
    else:
        new_h = IMAGE_SIZE
        new_w = int(round(w * IMAGE_SIZE / h))
    img = img.resize((new_w, new_h), Image.BILINEAR)

    # Center crop to 256x256.
    left = (new_w - IMAGE_SIZE) // 2
    top = (new_h - IMAGE_SIZE) // 2
    img = img.crop((left, top, left + IMAGE_SIZE, top + IMAGE_SIZE))

    arr = np.asarray(img, dtype=np.float32) / 255.0  # (H, W, 3), [0,1]
    arr = np.transpose(arr, (2, 0, 1))  # (3, H, W)
    arr = np.expand_dims(arr, axis=0)   # (1, 3, H, W)
    return arr


# ---------------------------------------------------------------------------
# Embedding + similarity
# ---------------------------------------------------------------------------


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n


def embed(image_bytes: bytes) -> np.ndarray:
    """Return the L2-normalized 512-dim float32 embedding for an image.

    Raises RuntimeError if the model isn't ready. Caller should either warm
    it up first (via warmup_async on startup) or call ensure_ready() and
    surface the loading state to the user."""
    if not ensure_ready():
        raise RuntimeError(_load_error or "MobileCLIP model not loaded")

    inp = _preprocess(image_bytes)
    outputs = _session.run(None, {_input_name: inp})
    # Xenova/mobileclip_s0 vision_model returns a single (1, 512) tensor.
    vec = np.asarray(outputs[0]).squeeze().astype(np.float32)
    return _l2_normalize(vec)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity for L2-normalized vectors == dot product."""
    return float(np.dot(a, b))


def to_bytes(vec: np.ndarray) -> bytes:
    """Serialize a 512-dim float32 vector for DB storage. 2048 bytes."""
    v = np.asarray(vec, dtype=np.float32)
    if v.shape != (EMBEDDING_DIM,):
        raise ValueError(f"expected shape ({EMBEDDING_DIM},), got {v.shape}")
    return v.tobytes()


def from_bytes(blob: bytes) -> np.ndarray:
    """Deserialize from DB back to a numpy vector."""
    v = np.frombuffer(blob, dtype=np.float32)
    if v.shape != (EMBEDDING_DIM,):
        raise ValueError(f"expected {EMBEDDING_DIM} floats, got {v.shape}")
    return v


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


@dataclass
class RankedMatch:
    product_id: int
    similarity: float

    def to_dict(self) -> dict:
        return {"product_id": self.product_id, "similarity": round(self.similarity, 4)}


def rank(query_embedding: np.ndarray, candidates: list[tuple[int, np.ndarray]], top_n: int = 10) -> list[RankedMatch]:
    """Rank (product_id, embedding) pairs by cosine similarity to the query."""
    scored = [
        RankedMatch(product_id=pid, similarity=cosine_similarity(query_embedding, emb))
        for pid, emb in candidates
    ]
    scored.sort(key=lambda m: -m.similarity)
    return scored[:top_n]
