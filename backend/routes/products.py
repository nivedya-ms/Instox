from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..database.db import db
from ..models.category import Category
from ..models.product import Product
from ..utils.price_calculator import calculate_retail_price

bp = Blueprint("products", __name__)


def _parse_decimal(value, field):
    if value is None or value == "":
        raise ValueError(f"{field} is required")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f"{field} must be a number")
    if d < 0:
        raise ValueError(f"{field} must be >= 0")
    return d


def _parse_int(value, field, default=None, allow_none=False):
    if value is None or value == "":
        if allow_none:
            return default
        raise ValueError(f"{field} is required")
    try:
        i = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer")
    if i < 0:
        raise ValueError(f"{field} must be >= 0")
    return i


def _resolve_category(category_id):
    if category_id in (None, "", 0):
        return None
    cat = Category.query.filter_by(id=int(category_id), user_id=current_user.id).first()
    if cat is None:
        raise ValueError("Category not found")
    return cat.id


@bp.get("")
@login_required
def list_products():
    q = Product.query.filter_by(user_id=current_user.id)
    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    cat = request.args.get("category")
    if cat:
        q = q.filter(Product.category_id == int(cat))
    page = max(1, int(request.args.get("page", 1)))
    limit = min(100, max(1, int(request.args.get("limit", 50))))
    total = q.count()
    items = q.order_by(Product.name).offset((page - 1) * limit).limit(limit).all()
    threshold = int(current_user.low_stock_threshold)
    return jsonify(
        {
            "success": True,
            "data": [p.to_dict(threshold=threshold) for p in items],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
        }
    )


@bp.get("/search")
@login_required
def search_products():
    q_str = (request.args.get("q") or "").strip()
    if not q_str:
        return jsonify({"success": True, "data": []})
    like = f"%{q_str}%"
    items = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        .order_by(Product.name)
        .limit(20)
        .all()
    )
    threshold = int(current_user.low_stock_threshold)
    return jsonify({"success": True, "data": [p.to_dict(threshold=threshold) for p in items]})


@bp.get("/low-stock")
@login_required
def low_stock():
    threshold_arg = request.args.get("threshold")
    if threshold_arg is None or threshold_arg == "":
        threshold = int(current_user.low_stock_threshold)
    else:
        try:
            threshold = int(threshold_arg)
            if threshold < 0:
                raise ValueError
        except ValueError:
            return jsonify({"success": False, "error": "threshold must be a non-negative integer"}), 400
    items = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(Product.quantity <= threshold)
        .order_by(Product.quantity, Product.name)
        .all()
    )
    out_of_stock = [p.to_dict(threshold=threshold) for p in items if p.quantity <= 0]
    low = [p.to_dict(threshold=threshold) for p in items if p.quantity > 0]
    return jsonify(
        {
            "success": True,
            "data": {
                "threshold": threshold,
                "out_of_stock_count": len(out_of_stock),
                "low_count": len(low),
                "total_count": len(items),
                "out_of_stock": out_of_stock,
                "low": low,
                "items": out_of_stock + low,
            },
        }
    )


@bp.get("/<int:product_id>")
@login_required
def get_product(product_id):
    p = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
    if p is None:
        return jsonify({"success": False, "error": "Product not found"}), 404
    return jsonify(
        {"success": True, "data": p.to_dict(threshold=int(current_user.low_stock_threshold))}
    )


@bp.post("")
@login_required
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    try:
        cost = _parse_decimal(data.get("cost_price"), "cost_price")
        quantity = _parse_int(data.get("quantity"), "quantity", default=0, allow_none=True) or 0
        category_id = _resolve_category(data.get("category_id"))
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    if "retail_price" in data and data["retail_price"] not in (None, ""):
        try:
            retail = _parse_decimal(data.get("retail_price"), "retail_price")
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
    else:
        retail = calculate_retail_price(cost, current_user.profit_percentage)

    product = Product(
        user_id=current_user.id,
        category_id=category_id,
        name=name,
        description=(data.get("description") or "").strip() or None,
        cost_price=cost,
        retail_price=retail,
        quantity=quantity,
        sku=(data.get("sku") or "").strip() or None,
    )
    db.session.add(product)
    db.session.commit()
    return (
        jsonify(
            {"success": True, "data": product.to_dict(threshold=int(current_user.low_stock_threshold))}
        ),
        201,
    )


@bp.put("/<int:product_id>")
@login_required
def update_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
    if product is None:
        return jsonify({"success": False, "error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return jsonify({"success": False, "error": "Name cannot be empty"}), 400
            product.name = name
        if "description" in data:
            product.description = (data.get("description") or "").strip() or None
        if "sku" in data:
            product.sku = (data.get("sku") or "").strip() or None
        if "category_id" in data:
            product.category_id = _resolve_category(data.get("category_id"))
        if "quantity" in data:
            product.quantity = _parse_int(data.get("quantity"), "quantity")

        cost_changed = False
        if "cost_price" in data:
            product.cost_price = _parse_decimal(data.get("cost_price"), "cost_price")
            cost_changed = True
        if "retail_price" in data and data["retail_price"] not in (None, ""):
            product.retail_price = _parse_decimal(data.get("retail_price"), "retail_price")
        elif cost_changed:
            product.retail_price = calculate_retail_price(
                product.cost_price, current_user.profit_percentage
            )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    db.session.commit()
    return jsonify(
        {"success": True, "data": product.to_dict(threshold=int(current_user.low_stock_threshold))}
    )


@bp.delete("/<int:product_id>")
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
    if product is None:
        return jsonify({"success": False, "error": "Product not found"}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({"success": True})


@bp.post("/calculate-price")
@login_required
def calculate_price_endpoint():
    data = request.get_json(silent=True) or {}
    try:
        cost = _parse_decimal(data.get("cost_price"), "cost_price")
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    pct = data.get("profit_percentage")
    if pct in (None, ""):
        pct = current_user.profit_percentage
    try:
        pct = Decimal(str(pct))
    except (InvalidOperation, TypeError):
        return jsonify({"success": False, "error": "Invalid profit_percentage"}), 400
    set_size = data.get("set_size")
    if set_size in (None, "", 0):
        set_size = 1
    try:
        set_size = int(set_size)
        if set_size <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "set_size must be a positive integer"}), 400

    unit_cost = cost / Decimal(set_size)
    retail = calculate_retail_price(unit_cost, pct)
    return jsonify(
        {
            "success": True,
            "data": {
                "unit_cost": float(unit_cost),
                "retail_price": float(retail),
                "profit_per_unit": float(retail - unit_cost),
                "profit_percentage": float(pct),
            },
        }
    )
