"""Photo → items → catalog match pipeline.

Flow:
  1. Vision LLM sees the counter photo and returns a JSON list:
     [{description, quantity, confidence, category_hint}, ...]
  2. Each proposal is fuzzy-matched against the user's product catalog by
     token overlap on (name, description, category_name), with a bonus for
     category-name matches.
  3. A proposal is auto-picked when the top match's normalized score is above
     `auto_pick_threshold`. Otherwise we return the top-N candidates so the
     UI can ask the owner to choose.

This module does NO natural-language understanding on its own — that's the
LLM's job. The matcher is deliberately simple (bag-of-words) so it stays
predictable and testable. When the catalog grows past ~1000 products,
swap the matcher for a CLIP-embedding nearest-neighbor. The pipeline
signature stays the same.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from ..models.product import Product
from .llm import LLMError, VisionLLMClient


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "with", "for", "to",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "some", "few", "several", "many", "item", "items", "thing", "things",
    "pair", "pairs", "piece", "pieces", "meter", "meters", "counter", "shop",
}


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class MatchCandidate:
    product_id: int
    unique_id: str
    name: str
    photo_url: Optional[str]
    retail_price: float
    quantity: int
    unit: str
    category_name: Optional[str]
    score: float  # 0..1

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "unique_id": self.unique_id,
            "name": self.name,
            "photo_url": self.photo_url,
            "retail_price": self.retail_price,
            "quantity": self.quantity,
            "unit": self.unit,
            "category_name": self.category_name,
            "score": round(self.score, 3),
        }


@dataclass
class Proposal:
    description: str
    quantity: int
    confidence: float  # 0..1 — combined vision confidence * match confidence
    candidates: List[MatchCandidate]
    auto_pick: bool  # True when top candidate is high-confidence enough

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "confidence": round(self.confidence, 3),
            "auto_pick": self.auto_pick,
            "candidates": [c.to_dict() for c in self.candidates],
        }


@dataclass
class IdentifyResult:
    proposals: List[Proposal] = field(default_factory=list)
    error: Optional[str] = None
    used_stub: bool = False

    def to_dict(self) -> dict:
        return {
            "proposals": [p.to_dict() for p in self.proposals],
            "error": self.error,
            "used_stub": self.used_stub,
        }


# ---------------------------------------------------------------------------
# Vision prompt & JSON parsing
# ---------------------------------------------------------------------------


_VISION_SYSTEM = (
    "You are a shop assistant helping a shop owner identify items placed on the "
    "billing counter. Your job is to identify every distinct retail item visible "
    "in the photo and count how many of each are present. "
    "\n\n"
    "For each distinct item, output ONE JSON object with these fields:\n"
    "  description       — short 2-6 word retail description (e.g. 'blue cotton curtain'\n"
    "                      or 'brown leather chappal'). Include colour and material if visible.\n"
    "  quantity          — integer, how many of this item are visible.\n"
    "  confidence        — number between 0 and 1, how sure you are.\n"
    "  category_hint     — short lowercase category name if obvious (curtains, footwear,\n"
    "                      fabrics, home textiles, accessories, sarees, blouses, or null).\n"
    "\n"
    "Return ONLY a JSON array of these objects. No prose, no markdown fences. "
    "If the photo has no retail items, return []."
)


def _build_vision_messages(photo_bytes: bytes, mime_type: str, mode: str) -> List[dict]:
    b64 = base64.b64encode(photo_bytes).decode("ascii")
    user_text = (
        "Identify every distinct retail item in this counter photo and count them."
        if mode != "single"
        else "Identify the one item in this photo. Return a single-object JSON array."
    )
    return [
        {"role": "system", "content": _VISION_SYSTEM},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                },
            ],
        },
    ]


def _extract_json_array(text: str) -> Optional[list]:
    """Tolerate ```json fences and stray prose around the JSON."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
    payload = fenced.group(1) if fenced else None
    if payload is None:
        # First balanced [...] block
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            payload = text[start : end + 1]
    if payload is None:
        return None
    try:
        val = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return val if isinstance(val, list) else None


# ---------------------------------------------------------------------------
# Catalog matching (bag-of-words, category-bonus)
# ---------------------------------------------------------------------------


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(s: str) -> List[str]:
    if not s:
        return []
    return [t for t in _TOKEN_RE.findall(s.lower()) if t not in _STOPWORDS and len(t) > 1]


def _score_candidate(
    query_tokens: List[str],
    category_hint: Optional[str],
    product: Product,
) -> float:
    """Score in [0, 1]. Combines token overlap on name+description with a
    category-match bonus."""
    if not query_tokens:
        return 0.0

    name_tokens = set(_tokenize(product.name or ""))
    desc_tokens = set(_tokenize(product.description or ""))
    cat_name = product.category.name if product.category else ""
    cat_tokens = set(_tokenize(cat_name))

    q = set(query_tokens)
    name_overlap = len(q & name_tokens)
    desc_overlap = len(q & desc_tokens)
    cat_overlap = len(q & cat_tokens)

    # Weighted overlap: name matches count most, then description.
    weighted = name_overlap * 3.0 + desc_overlap * 1.0 + cat_overlap * 2.0
    denom = len(q) * 3.0  # perfect score = every query token matches the name

    score = min(1.0, weighted / denom) if denom > 0 else 0.0

    # Category-hint bonus: if the LLM's category_hint contains a token that
    # appears in the product's category name, boost.
    if category_hint and cat_name:
        hint_tokens = set(_tokenize(category_hint))
        if hint_tokens & cat_tokens:
            score = min(1.0, score + 0.15)

    return score


def match_catalog(
    description: str,
    category_hint: Optional[str],
    catalog: Iterable[Product],
    top_n: int = 3,
    min_score: float = 0.15,
) -> List[MatchCandidate]:
    tokens = _tokenize(description)
    if not tokens:
        return []
    scored: List[tuple[float, Product]] = []
    for p in catalog:
        s = _score_candidate(tokens, category_hint, p)
        if s >= min_score:
            scored.append((s, p))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [
        MatchCandidate(
            product_id=p.id,
            unique_id=p.unique_id or "",
            name=p.name,
            photo_url=p.photo_url,
            retail_price=float(p.retail_price),
            quantity=p.quantity,
            unit=(p.category.unit if p.category else None) or "pieces",
            category_name=p.category.name if p.category else None,
            score=s,
        )
        for s, p in scored[:top_n]
    ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def identify_from_photo(
    photo_bytes: bytes,
    mime_type: str,
    catalog: Iterable[Product],
    llm: VisionLLMClient,
    mode: str = "multi",
    auto_pick_threshold: float = 0.85,
    max_items: int = 8,
    max_candidates: int = 3,
    used_stub: bool = False,
) -> IdentifyResult:
    """Run the vision → catalog pipeline.

    Never raises for the expected error modes (bad LLM output, LLM failure) —
    surfaces them through `IdentifyResult.error` with an empty proposal list
    so the UI can show a helpful message and fall back to manual search.
    """
    messages = _build_vision_messages(photo_bytes, mime_type, mode)
    try:
        raw = llm.complete(messages, temperature=0.0, max_tokens=500)
    except LLMError as e:
        return IdentifyResult(error=f"vision LLM failed: {e}", used_stub=used_stub)

    items = _extract_json_array(raw)
    if items is None:
        return IdentifyResult(
            error="Could not parse a JSON array from the model output.",
            used_stub=used_stub,
        )

    catalog_list = list(catalog)
    proposals: List[Proposal] = []
    for entry in items[:max_items]:
        if not isinstance(entry, dict):
            continue
        description = str(entry.get("description") or "").strip()
        if not description:
            continue
        try:
            quantity = max(1, int(entry.get("quantity") or 1))
        except (TypeError, ValueError):
            quantity = 1
        try:
            vision_conf = float(entry.get("confidence") or 0.5)
        except (TypeError, ValueError):
            vision_conf = 0.5
        vision_conf = max(0.0, min(1.0, vision_conf))
        category_hint = entry.get("category_hint")
        if category_hint is not None:
            category_hint = str(category_hint).strip() or None

        candidates = match_catalog(
            description=description,
            category_hint=category_hint,
            catalog=catalog_list,
            top_n=max_candidates,
        )

        top_score = candidates[0].score if candidates else 0.0
        second_score = candidates[1].score if len(candidates) > 1 else 0.0

        # Combined confidence = vision confidence × how clearly the top match
        # beats the runner-up. When there's only one candidate, use raw score.
        if not candidates:
            combined = 0.0
        elif len(candidates) == 1:
            combined = vision_conf * top_score
        else:
            gap_ratio = top_score / (top_score + second_score) if (top_score + second_score) > 0 else 0
            combined = vision_conf * ((top_score + gap_ratio) / 2)

        auto_pick = bool(candidates) and combined >= auto_pick_threshold

        proposals.append(
            Proposal(
                description=description,
                quantity=quantity,
                confidence=combined,
                candidates=candidates,
                auto_pick=auto_pick,
            )
        )

    return IdentifyResult(proposals=proposals, used_stub=used_stub)
