from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from ..database.db import db
from ..models.product import Product
from ..models.sale import Sale, SaleItem

bp = Blueprint("sales", __name__)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


@bp.get("")
@login_required
def list_sales():
    q = Sale.query.filter_by(user_id=current_user.id)
    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if start:
        q = q.filter(Sale.created_at >= start)
    if end:
        q = q.filter(Sale.created_at < end + timedelta(days=1))
    page = max(1, int(request.args.get("page", 1)))
    limit = min(100, max(1, int(request.args.get("limit", 50))))
    total = q.count()
    sales = q.order_by(Sale.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return jsonify(
        {
            "success": True,
            "data": [s.to_dict() for s in sales],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
        }
    )


@bp.get("/today")
@login_required
def today_sales():
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sales = (
        Sale.query.filter_by(user_id=current_user.id)
        .filter(Sale.created_at >= start)
        .order_by(Sale.created_at.desc())
        .all()
    )
    total = sum((float(s.total_amount) for s in sales), 0.0)
    profit = sum((float(s.total_profit) for s in sales), 0.0)
    return jsonify(
        {
            "success": True,
            "data": {
                "count": len(sales),
                "total_amount": total,
                "total_profit": profit,
                "sales": [s.to_dict() for s in sales],
            },
        }
    )


@bp.get("/summary")
@login_required
def summary():
    period = request.args.get("period", "daily")
    now = datetime.utcnow()
    if period == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total, profit, count = (
        db.session.query(
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.coalesce(func.sum(Sale.total_profit), 0),
            func.count(Sale.id),
        )
        .filter(Sale.user_id == current_user.id, Sale.created_at >= start)
        .one()
    )
    return jsonify(
        {
            "success": True,
            "data": {
                "period": period,
                "since": start.isoformat(),
                "total_sales": float(total),
                "total_profit": float(profit),
                "sale_count": int(count),
            },
        }
    )


@bp.get("/<int:sale_id>")
@login_required
def get_sale(sale_id):
    sale = Sale.query.filter_by(id=sale_id, user_id=current_user.id).first()
    if sale is None:
        return jsonify({"success": False, "error": "Sale not found"}), 404
    return jsonify({"success": True, "data": sale.to_dict()})


@bp.post("")
@login_required
def create_sale():
    data = request.get_json(silent=True) or {}
    items_in = data.get("items") or []
    if not items_in:
        return jsonify({"success": False, "error": "At least one item is required"}), 400

    customer_name = (data.get("customer_name") or "").strip() or None
    total_amount = Decimal("0")
    total_profit = Decimal("0")
    sale_items = []

    product_ids = []
    for raw in items_in:
        pid = raw.get("product_id")
        try:
            qty = int(raw.get("quantity", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Quantity must be an integer"}), 400
        if not pid or qty <= 0:
            return jsonify({"success": False, "error": "product_id and quantity > 0 required"}), 400
        product_ids.append((int(pid), qty))

    products = {
        p.id: p
        for p in Product.query.filter(
            Product.user_id == current_user.id,
            Product.id.in_([pid for pid, _ in product_ids]),
        )
        .with_for_update()
        .all()
    }

    for pid, qty in product_ids:
        product = products.get(pid)
        if product is None:
            return jsonify({"success": False, "error": f"Product {pid} not found"}), 404
        if product.quantity < qty:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Insufficient stock for {product.name} (have {product.quantity})",
                    }
                ),
                400,
            )
        unit_price = Decimal(str(product.retail_price))
        unit_cost = Decimal(str(product.cost_price))
        line_total = unit_price * qty
        line_profit = (unit_price - unit_cost) * qty
        total_amount += line_total
        total_profit += line_profit
        sale_items.append(
            SaleItem(
                product_id=product.id,
                product_name=product.name,
                quantity=qty,
                unit_price=unit_price,
                unit_cost=unit_cost,
                profit=line_profit,
            )
        )
        product.quantity -= qty

    sale = Sale(
        user_id=current_user.id,
        customer_name=customer_name,
        total_amount=total_amount,
        total_profit=total_profit,
        items=sale_items,
    )
    db.session.add(sale)
    db.session.commit()
    return jsonify({"success": True, "data": sale.to_dict()}), 201


@bp.get("/<int:sale_id>/bill")
@login_required
def customer_bill(sale_id):
    """Customer-facing bill — strips cost and profit."""
    sale = Sale.query.filter_by(id=sale_id, user_id=current_user.id).first()
    if sale is None:
        return jsonify({"success": False, "error": "Sale not found"}), 404
    return jsonify({"success": True, "data": sale.to_dict(include_profit=False)})
