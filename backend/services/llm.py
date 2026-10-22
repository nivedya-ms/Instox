"""LLM client abstraction.

Design: one generic OpenAI-compatible client backs all real providers
(DeepSeek, Qwen/DashScope, Zhipu, OpenAI, local vLLM, ...). Configuration is
driven by `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` for text, with
`VISION_*` overrides for the vision-capable model (which may differ from
the text model on the same provider — e.g. `qwen-plus` for text but
`qwen-vl-plus` for vision).

`LLM_PROVIDER=stub` short-circuits both text and vision to deterministic
canned responses so tests and initial UX validation run offline.
"""

from __future__ import annotations

import re
from typing import List, Optional


class LLMError(RuntimeError):
    pass


class LLMClient:
    def complete(
        self,
        messages: List[dict],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> str:
        raise NotImplementedError


class VisionLLMClient(LLMClient):
    """Same surface as `LLMClient`, but accepts messages with image content
    parts in the OpenAI multimodal format:

        {"role": "user", "content": [
            {"type": "text", "text": "..."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
        ]}
    """


class OpenAICompatibleLLM(LLMClient):
    def __init__(self, api_key: str, base_url: str, model: str):
        if not api_key:
            raise LLMError(
                "LLM_API_KEY is not set. Either export a key or leave LLM_PROVIDER=stub."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def complete(self, messages, temperature=0.1, max_tokens=500):
        try:
            r = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMError(f"LLM request failed: {e}") from e
        return (r.choices[0].message.content or "").strip()


class OpenAICompatibleVisionLLM(OpenAICompatibleLLM, VisionLLMClient):
    """Vision-capable client. Identical implementation — the model + messages
    do all the work."""


# ---------------------------------------------------------------------------
# Stub — pattern-based fake for offline testing.
# ---------------------------------------------------------------------------


class StubLLM(LLMClient):
    _SQL_SENTINEL = "-- STUB: I don't know how to answer this yet"

    def complete(self, messages, temperature=0.1, max_tokens=500):
        role_content = {m["role"]: m.get("content", "") for m in messages}
        system = str(role_content.get("system", ""))
        user = _flatten_content(role_content.get("user", ""))

        sys_l = system.lower()
        if "you are a sql assistant" in sys_l:
            return self._canned_sql(user.lower())
        if "you explain shop data" in sys_l:
            return self._canned_answer(user)
        if "you are a shop assistant" in sys_l and "identify" in sys_l:
            return self._canned_vision(user)
        return self._SQL_SENTINEL

    # SQL generation stub
    def _canned_sql(self, q: str) -> str:
        if re.search(r"\btoday\b", q):
            if "profit" in q:
                return (
                    "SELECT COALESCE(SUM(total_amount), 0) AS sales, "
                    "COALESCE(SUM(total_profit), 0) AS profit, "
                    "COUNT(*) AS sale_count "
                    "FROM my_sales WHERE DATE(created_at) = DATE('now')"
                )
            return (
                "SELECT COALESCE(SUM(total_amount), 0) AS sales, COUNT(*) AS sale_count "
                "FROM my_sales WHERE DATE(created_at) = DATE('now')"
            )
        if "this month" in q or "monthly" in q or "month" in q:
            return (
                "SELECT COALESCE(SUM(total_amount), 0) AS sales, "
                "COALESCE(SUM(total_profit), 0) AS profit, "
                "COUNT(*) AS sale_count "
                "FROM my_sales WHERE created_at >= date('now', 'start of month')"
            )
        if re.search(r"\b(best|top|most)\b", q) and re.search(r"(sell|sold|selling|product)", q):
            return (
                "SELECT product_name, SUM(quantity) AS units_sold, SUM(profit) AS profit "
                "FROM my_sale_items GROUP BY product_name ORDER BY units_sold DESC LIMIT 5"
            )
        if "low stock" in q or "out of stock" in q or "running out" in q:
            return (
                "SELECT name, unique_id, quantity FROM my_products "
                "WHERE quantity <= 5 ORDER BY quantity ASC LIMIT 20"
            )
        if re.search(r"how many products|total products|number of products", q):
            return "SELECT COUNT(*) AS total_products FROM my_products"
        if "total profit" in q or "all-time profit" in q or "lifetime profit" in q:
            return "SELECT COALESCE(SUM(total_profit), 0) AS profit FROM my_sales"
        if "purchase list" in q or "to buy" in q:
            return (
                "SELECT item_name, quantity, is_purchased FROM my_purchase_list "
                "ORDER BY is_purchased, created_at DESC"
            )
        return self._SQL_SENTINEL

    def _canned_answer(self, user_prompt: str) -> str:
        m = re.search(r"Result:\s*(.*?)(?:\n\s*Reply.*)?$", user_prompt, re.DOTALL)
        if not m:
            return "Here's what I found."
        result = m.group(1).strip()
        if not result or result.startswith("(no data)"):
            return "No data yet for that question."
        return f"Here are the numbers from your data:\n{result}"

    # Vision stub — returns canned proposals so the billing UI can be exercised
    # without any API key. Real vision LLM output has to be JSON-parseable in the
    # same shape (see photo_match.py).
    def _canned_vision(self, user_prompt: str) -> str:
        low = user_prompt.lower()
        if "one item" in low or "single item" in low:
            return (
                '[{"description": "one item on the counter", "quantity": 1, '
                '"confidence": 0.7, "category_hint": null}]'
            )
        # Multi-item default: pretend we saw two curtain-like items and one sheet.
        return (
            "["
            '{"description": "blue curtain", "quantity": 2, "confidence": 0.9, '
            '"category_hint": "curtains"},'
            '{"description": "white bedsheet", "quantity": 1, "confidence": 0.6, '
            '"category_hint": "home textiles"}'
            "]"
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _flatten_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                out.append(part.get("text", ""))
        return "\n".join(out)
    return str(content)


def get_llm(app_config: dict) -> LLMClient:
    provider = (app_config.get("LLM_PROVIDER") or "stub").lower()
    if provider == "stub":
        return StubLLM()
    api_key = app_config.get("LLM_API_KEY") or ""
    base_url = app_config.get("LLM_BASE_URL") or "https://api.openai.com/v1"
    model = app_config.get("LLM_MODEL") or "gpt-4o-mini"
    return OpenAICompatibleLLM(api_key=api_key, base_url=base_url, model=model)


def get_vision_llm(app_config: dict) -> VisionLLMClient:
    provider = (app_config.get("LLM_PROVIDER") or "stub").lower()
    if provider == "stub":
        # Vision stub reuses the same StubLLM; the caller must set the system
        # prompt so `complete()` routes to _canned_vision.
        return _StubVisionLLM()
    api_key = app_config.get("VISION_API_KEY") or app_config.get("LLM_API_KEY") or ""
    base_url = (
        app_config.get("VISION_BASE_URL")
        or app_config.get("LLM_BASE_URL")
        or "https://api.openai.com/v1"
    )
    model = app_config.get("VISION_MODEL") or "gpt-4o-mini"
    return OpenAICompatibleVisionLLM(api_key=api_key, base_url=base_url, model=model)


class _StubVisionLLM(StubLLM, VisionLLMClient):
    pass
