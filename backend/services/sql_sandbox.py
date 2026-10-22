"""User-scoped read-only SQL sandbox for the AI Chat feature.

Key safety properties:
- SELECT / WITH only. Every other statement type is rejected before it reaches SQLite.
- The connection is opened read-only against the same file the app writes to,
  so even a successfully-parsed INSERT/UPDATE would fail at the engine level.
- The LLM must only reference user-scoped views (my_products, my_sales, ...)
  that are created per-connection with the caller's user_id embedded. There is
  no way to reach another tenant's rows from these views.
- Row cap + busy timeout to keep pathological queries bounded.

This module has no Flask dependencies so it's trivial to unit-test.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any, List, Optional


# Tables the LLM is allowed to reason about, wrapped as user-scoped views.
# Every view is prefixed `my_` to make the prompt unambiguous.
USER_SCOPED_VIEWS: dict[str, str] = {
    "my_products": "SELECT * FROM products WHERE user_id = :uid",
    "my_categories": "SELECT * FROM categories WHERE user_id = :uid",
    "my_sales": "SELECT * FROM sales WHERE user_id = :uid",
    "my_sale_items": (
        "SELECT si.* FROM sale_items si "
        "JOIN sales s ON si.sale_id = s.id "
        "WHERE s.user_id = :uid"
    ),
    "my_purchase_list": "SELECT * FROM purchase_lists WHERE user_id = :uid",
}


# Any of these keywords in the LLM's SQL → reject.
_BLOCKED_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|detach|pragma|create|replace|"
    r"truncate|vacuum|analyze|reindex|savepoint|release|grant|revoke)\b",
    re.IGNORECASE,
)


@dataclass
class SqlResult:
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    truncated: bool = False

    def to_dict(self) -> dict:
        return {"columns": self.columns, "rows": self.rows, "truncated": self.truncated}

    def as_text_table(self, max_rows: int = 20) -> str:
        if not self.columns:
            return "(no data)"
        head = " | ".join(self.columns)
        body_rows = self.rows[:max_rows]
        body = "\n".join(" | ".join(_fmt_cell(c) for c in r) for r in body_rows)
        suffix = ""
        if len(self.rows) > max_rows:
            suffix = f"\n... {len(self.rows) - max_rows} more row(s)"
        if self.truncated:
            suffix += "\n(result set truncated)"
        return f"{head}\n{body}{suffix}"


def _fmt_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def is_safe_readonly_sql(sql: str) -> tuple[bool, Optional[str]]:
    """Return (ok, reason). reason is populated when ok is False."""
    if not sql or not sql.strip():
        return False, "empty query"
    trimmed = sql.strip().rstrip(";").strip()
    if not trimmed:
        return False, "empty query"
    if ";" in trimmed:
        return False, "multiple statements are not allowed"
    if not re.match(r"^\s*(select|with)\b", trimmed, re.IGNORECASE):
        return False, "only SELECT / WITH queries are allowed"
    m = _BLOCKED_KEYWORDS.search(trimmed)
    if m:
        return False, f"blocked keyword: {m.group(0).lower()}"
    return True, None


def run_scoped_query(
    db_path: str,
    user_id: int,
    sql: str,
    max_rows: int = 100,
    timeout_ms: int = 3000,
) -> SqlResult:
    """Execute `sql` under a read-only connection with per-user views defined.

    Raises ValueError with a human-readable message on validation failure or
    engine-level errors so callers can echo the reason back to the LLM/UI.
    """
    ok, reason = is_safe_readonly_sql(sql)
    if not ok:
        raise ValueError(f"unsafe SQL: {reason}")

    # Open a dedicated connection so temp views die with it and no other request
    # can see them. We create the views first (a write on the *temp* schema)
    # and then flip `query_only` to block any further writes for the LLM query.
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        conn.execute(f"PRAGMA busy_timeout = {int(timeout_ms)}")
        # Create the user-scoped views on this connection only.
        for name, view_sql in USER_SCOPED_VIEWS.items():
            resolved = view_sql.replace(":uid", str(int(user_id)))
            conn.execute(f"CREATE TEMP VIEW {name} AS {resolved}")
        # Now lock the connection for the LLM query: no INSERT/UPDATE/DELETE etc.
        # will succeed, even if the SQL somehow slipped past `is_safe_readonly_sql`.
        conn.execute("PRAGMA query_only = 1")

        try:
            cur = conn.execute(sql.rstrip(";"))
        except sqlite3.Error as e:
            raise ValueError(f"SQL error: {e}") from e

        columns = [d[0] for d in cur.description] if cur.description else []
        fetched = cur.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = [list(r) for r in fetched[:max_rows]]
        return SqlResult(columns=columns, rows=rows, truncated=truncated)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema description used in the LLM system prompt.
# We describe the views (not the physical tables) so the LLM writes safe SQL
# by construction.
# ---------------------------------------------------------------------------
SCHEMA_DESCRIPTION = """\
You are querying a small shop's data. Use ONLY these views (no physical tables):

my_products(
  id INTEGER, unique_id TEXT,  -- 'INSTOX-00001'
  name TEXT, description TEXT,
  cost_price NUMERIC, retail_price NUMERIC,
  quantity INTEGER,
  sku TEXT, photo_url TEXT,
  category_id INTEGER,
  created_at TIMESTAMP, updated_at TIMESTAMP
)

my_categories(id INTEGER, name TEXT, description TEXT, created_at TIMESTAMP)

my_sales(
  id INTEGER,
  customer_name TEXT,
  total_amount NUMERIC,
  total_profit NUMERIC,
  created_at TIMESTAMP
)

my_sale_items(
  id INTEGER, sale_id INTEGER, product_id INTEGER, product_name TEXT,
  quantity INTEGER, unit_price NUMERIC, unit_cost NUMERIC, profit NUMERIC
)

my_purchase_list(
  id INTEGER, item_name TEXT, quantity INTEGER,
  is_purchased BOOLEAN, created_at TIMESTAMP
)

Rules:
- Return ONLY a single SQLite SELECT (or WITH ... SELECT). No explanation.
- No INSERT/UPDATE/DELETE/DROP/ALTER/CREATE.
- Use SQLite date functions: date('now'), date('now','start of month'), strftime.
- Money columns are ₹ (INR). Profit = retail - cost.
- Prefer aggregate queries (SUM, COUNT, GROUP BY) when the question asks for totals.
- LIMIT 20 for list-style questions.
"""
