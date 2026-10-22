"""Lightweight local image matching.

Ships with a real, deterministic pHash implementation. MobileCLIP-style
embeddings can be layered on later behind the same interface — this module
defines `SimilarityMethod` so we can add methods without touching callers.

pHash design (matches the canonical 64-bit variant so browser + server
produce identical hashes):
  1. Convert image to greyscale.
  2. Resize to 32x32 with bilinear interpolation.
  3. Compute a 32x32 DCT (Type-II, orthonormal), take the 8x8 low-frequency
     top-left corner.
  4. Compute the median of the 64 coefficients (excluding DC[0,0]).
  5. Each coefficient becomes a bit: 1 if > median, 0 otherwise. 64 bits → hash.

Distance metric: Hamming distance in [0, 64]. Similarity = 1 - hamming / 64.
"""

from __future__ import annotations

import io
import math
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

from PIL import Image


# ---------------------------------------------------------------------------
# pHash
# ---------------------------------------------------------------------------


_DCT_SIZE = 32
_HASH_SIZE = 8  # 8x8 = 64 bits


def _dct_1d(vec: list[float]) -> list[float]:
    """1-D DCT-II with orthonormal normalization.

    Kept in pure Python (no numpy) so the server has zero heavy deps beyond
    Pillow. 32-point DCT runs in ~1 ms on CPython; we do 64 of them per hash
    (32 rows + 32 cols), so a full pHash is ~60-100 ms per image. Fine for
    the scales we care about (a few hundred products per shop).
    """
    N = len(vec)
    out = [0.0] * N
    factor = math.pi / (2 * N)
    for k in range(N):
        s = 0.0
        for n in range(N):
            s += vec[n] * math.cos(factor * (2 * n + 1) * k)
        if k == 0:
            out[k] = s * math.sqrt(1.0 / N)
        else:
            out[k] = s * math.sqrt(2.0 / N)
    return out


def _dct_2d(matrix: list[list[float]]) -> list[list[float]]:
    N = len(matrix)
    # DCT rows
    tmp = [_dct_1d(row) for row in matrix]
    # DCT columns
    cols = [[tmp[r][c] for r in range(N)] for c in range(N)]
    dcted_cols = [_dct_1d(col) for col in cols]
    out = [[dcted_cols[c][r] for c in range(N)] for r in range(N)]
    return out


def phash(image_bytes: bytes) -> int:
    """Return a 64-bit perceptual hash of an image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize(
        (_DCT_SIZE, _DCT_SIZE), Image.BILINEAR
    )
    matrix = [
        [float(img.getpixel((x, y))) for x in range(_DCT_SIZE)]
        for y in range(_DCT_SIZE)
    ]
    dct = _dct_2d(matrix)
    low_freq = [dct[y][x] for y in range(_HASH_SIZE) for x in range(_HASH_SIZE)]
    # Exclude the DC term (top-left) from the median for stability.
    non_dc = low_freq[1:]
    non_dc_sorted = sorted(non_dc)
    mid = len(non_dc_sorted) // 2
    median = (
        (non_dc_sorted[mid - 1] + non_dc_sorted[mid]) / 2.0
        if len(non_dc_sorted) % 2 == 0
        else non_dc_sorted[mid]
    )
    bits = 0
    for i, v in enumerate(low_freq):
        if v > median:
            bits |= 1 << (63 - i)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def similarity(a: int, b: int) -> float:
    """Cosine-esque similarity in [0, 1]. 1.0 = identical."""
    return 1.0 - hamming(a, b) / 64.0


def phash_hex(h: int) -> str:
    return f"{h:016x}"


def phash_from_hex(s: str) -> int:
    return int(s, 16)


# ---------------------------------------------------------------------------
# Ranking against a candidate set
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    """Anything with an id + hash. Callers wrap Product rows into this."""

    id: int
    label: str
    photo_url: Optional[str]
    phash: int
    extra: dict


@dataclass
class RankedMatch:
    id: int
    label: str
    photo_url: Optional[str]
    hamming: int
    similarity: float
    extra: dict

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "photo_url": self.photo_url,
            "hamming": self.hamming,
            "similarity": round(self.similarity, 4),
            **self.extra,
        }


@dataclass
class BenchmarkResult:
    method: str
    query_hash: str
    query_ms: float
    compare_ms: float
    total_ms: float
    candidate_count: int
    matches: List[RankedMatch]

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "query_hash": self.query_hash,
            "query_ms": round(self.query_ms, 3),
            "compare_ms": round(self.compare_ms, 3),
            "total_ms": round(self.total_ms, 3),
            "candidate_count": self.candidate_count,
            "matches": [m.to_dict() for m in self.matches],
        }


def rank_phash(
    query_bytes: bytes,
    candidates: Iterable[Candidate],
    top_n: int = 10,
) -> BenchmarkResult:
    t0 = time.perf_counter()
    q = phash(query_bytes)
    t1 = time.perf_counter()

    candidates = list(candidates)
    scored = [
        RankedMatch(
            id=c.id,
            label=c.label,
            photo_url=c.photo_url,
            hamming=hamming(q, c.phash),
            similarity=similarity(q, c.phash),
            extra=c.extra,
        )
        for c in candidates
    ]
    scored.sort(key=lambda m: m.hamming)
    t2 = time.perf_counter()

    return BenchmarkResult(
        method="phash",
        query_hash=phash_hex(q),
        query_ms=(t1 - t0) * 1000,
        compare_ms=(t2 - t1) * 1000,
        total_ms=(t2 - t0) * 1000,
        candidate_count=len(candidates),
        matches=scored[:top_n],
    )


# ---------------------------------------------------------------------------
# MobileCLIP hook (soft-loaded so unavailable install doesn't break imports)
# ---------------------------------------------------------------------------


def is_mobileclip_available() -> bool:
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    # We also need the ONNX weights on disk. For MVP we only report
    # availability of the runtime; the weight-loading path is a TODO once
    # the user gives the go-ahead based on pHash results.
    return True


def rank_mobileclip(query_bytes: bytes, candidates: Iterable[Candidate], top_n: int = 10):
    raise NotImplementedError(
        "MobileCLIP path is not yet wired up. Run pHash benchmark first "
        "to see if the accuracy is enough for your catalog."
    )
