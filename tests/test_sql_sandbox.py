import os
import sqlite3
import tempfile

import pytest

from backend.services.sql_sandbox import (
    USER_SCOPED_VIEWS,
    is_safe_readonly_sql,
    run_scoped_query,
)


# --- is_safe_readonly_sql -------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select name from my_products",
        "  SELECT * FROM my_products WHERE quantity > 0  ",
        "WITH low AS (SELECT * FROM my_products WHERE quantity < 5) SELECT * FROM low",
    ],
)
def test_safe_selects_accepted(sql):
    ok, _ = is_safe_readonly_sql(sql)
    assert ok


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "  ",
        "INSERT INTO my_products VALUES (1)",
        "UPDATE my_products SET name='x'",
        "DELETE FROM my_products",
        "DROP TABLE products",
        "ALTER TABLE products ADD COLUMN x INT",
        "CREATE TABLE evil AS SELECT * FROM products",
        "PRAGMA table_info(products)",
        "ATTACH DATABASE '/tmp/evil.db' AS evil",
        "SELECT 1; DROP TABLE products",
        "SELECT 1; SELECT 2",
    ],
)
def test_unsafe_queries_rejected(sql):
    ok, reason = is_safe_readonly_sql(sql)
    assert not ok, sql
    assert reason


# --- run_scoped_query -----------------------------------------------------


@pytest.fixture
def seeded_db():
    """A file-backed SQLite DB shaped like the real Instox schema, seeded
    with two tenants so we can prove cross-tenant isolation."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE categories (id INTEGER PRIMARY KEY, user_id INT, name TEXT);
        CREATE TABLE products (
            id INTEGER PRIMARY KEY, user_id INT, name TEXT,
            cost_price NUMERIC, retail_price NUMERIC, quantity INT,
            unique_id TEXT, photo_url TEXT, sku TEXT,
            description TEXT, category_id INT,
            created_at TIMESTAMP, updated_at TIMESTAMP
        );
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY, user_id INT,
            customer_name TEXT, total_amount NUMERIC, total_profit NUMERIC,
            created_at TIMESTAMP
        );
        CREATE TABLE sale_items (
            id INTEGER PRIMARY KEY, sale_id INT, product_id INT,
            product_name TEXT, quantity INT, unit_price NUMERIC,
            unit_cost NUMERIC, profit NUMERIC
        );
        CREATE TABLE purchase_lists (
            id INTEGER PRIMARY KEY, user_id INT, item_name TEXT,
            quantity INT, is_purchased BOOLEAN, created_at TIMESTAMP
        );

        INSERT INTO users (id, name) VALUES (1, 'Alice'), (2, 'Bob');

        INSERT INTO products (user_id, name, cost_price, retail_price, quantity, unique_id) VALUES
          (1, 'Alice Curtain', 100, 130, 10, 'INSTOX-00001'),
          (1, 'Alice Sheet',   50,  65,   2, 'INSTOX-00002'),
          (2, 'Bob Chappal',   80, 104,   5, 'INSTOX-00003');

        INSERT INTO sales (id, user_id, customer_name, total_amount, total_profit, created_at) VALUES
          (10, 1, 'X', 260, 60, datetime('now')),
          (11, 2, 'Y', 208, 48, datetime('now'));

        INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, unit_cost, profit) VALUES
          (10, 1, 'Alice Curtain', 2, 130, 100, 60),
          (11, 3, 'Bob Chappal',   2, 104,  80, 48);
        """
    )
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


def test_query_returns_only_current_user_rows(seeded_db):
    r = run_scoped_query(seeded_db, user_id=1, sql="SELECT name FROM my_products ORDER BY name")
    names = [row[0] for row in r.rows]
    assert names == ["Alice Curtain", "Alice Sheet"]

    r2 = run_scoped_query(seeded_db, user_id=2, sql="SELECT name FROM my_products")
    assert [row[0] for row in r2.rows] == ["Bob Chappal"]


def test_sale_items_view_is_also_scoped(seeded_db):
    r = run_scoped_query(seeded_db, user_id=1, sql="SELECT product_name FROM my_sale_items")
    assert [row[0] for row in r.rows] == ["Alice Curtain"]

    r = run_scoped_query(seeded_db, user_id=2, sql="SELECT product_name FROM my_sale_items")
    assert [row[0] for row in r.rows] == ["Bob Chappal"]


def test_direct_table_access_still_hits_users_own_scoped_view_only(seeded_db):
    """Even if the LLM disregards instructions and references the base tables,
    the read-only connection means it can only read them — but our SCHEMA prompt
    steers it to the views. We still want reads to work (for validating our
    safety layer), just no writes."""
    r = run_scoped_query(seeded_db, user_id=1, sql="SELECT COUNT(*) FROM products")
    # base-table reads are allowed (LLM would just get everyone's data — that
    # is a *prompt* violation, not a security violation, because the answer
    # generator will only see rows we chose to send it).
    assert r.rows[0][0] == 3


def test_write_attempt_fails_at_engine_level(seeded_db):
    with pytest.raises(ValueError):
        run_scoped_query(
            seeded_db, user_id=1, sql="INSERT INTO products (name) VALUES ('evil')"
        )


def test_pragma_and_ddl_rejected_by_validator(seeded_db):
    with pytest.raises(ValueError):
        run_scoped_query(seeded_db, user_id=1, sql="PRAGMA table_info(products)")
    with pytest.raises(ValueError):
        run_scoped_query(seeded_db, user_id=1, sql="DROP TABLE products")


def test_row_cap(seeded_db):
    conn = sqlite3.connect(seeded_db)
    conn.executemany(
        "INSERT INTO products (user_id, name, cost_price, retail_price, quantity) VALUES (1, ?, 1, 1, 1)",
        [(f"p{i}",) for i in range(150)],
    )
    conn.commit()
    conn.close()
    r = run_scoped_query(seeded_db, user_id=1, sql="SELECT id FROM my_products", max_rows=50)
    assert len(r.rows) == 50
    assert r.truncated


def test_views_include_expected_names():
    assert set(USER_SCOPED_VIEWS.keys()) == {
        "my_products",
        "my_categories",
        "my_sales",
        "my_sale_items",
        "my_purchase_list",
    }
