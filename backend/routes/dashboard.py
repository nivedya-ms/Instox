from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from ..database.db import db
from ..models.product import Product
from ..models.sale import Sale

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required
def dashboard():
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    override = request.args.get("low_stock_threshold")
    if override not in (None, ""):
        try:
            low_threshold = max(0, int(override))
        except ValueError:
            low_threshold = int(current_user.low_stock_threshold)
    else:
        low_threshold = int(current_user.low_stock_threshold)

    today_total, today_profit, today_count = (
        db.session.query(
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.coalesce(func.sum(Sale.total_profit), 0),
            func.count(Sale.id),
        )
        .filter(Sale.user_id == current_user.id, Sale.created_at >= today_start)
        .one()
    )
    month_total, month_profit, month_count = (
        db.session.query(
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.coalesce(func.sum(Sale.total_profit), 0),
            func.count(Sale.id),
        )
        .filter(Sale.user_id == current_user.id, Sale.created_at >= month_start)
        .one()
    )

    stock_value = (
        db.session.query(func.coalesce(func.sum(Product.cost_price * Product.quantity), 0))
        .filter(Product.user_id == current_user.id)
        .scalar()
    )
    total_products = (
        db.session.query(func.count(Product.id))
        .filter(Product.user_id == current_user.id)
        .scalar()
    )
    total_units = (
        db.session.query(func.coalesce(func.sum(Product.quantity), 0))
        .filter(Product.user_id == current_user.id)
        .scalar()
    )
    low_stock = (
        Product.query.filter_by(user_id=current_user.id)
        .filter(Product.quantity <= low_threshold)
        .order_by(Product.quantity, Product.name)
        .limit(50)
        .all()
    )
    out_of_stock_items = [p for p in low_stock if p.quantity <= 0]
    low_items = [p for p in low_stock if p.quantity > 0]

    last_7_days = []
    for i in range(6, -1, -1):
        day = (today_start - timedelta(days=i))
        next_day = day + timedelta(days=1)
        total, profit = (
            db.session.query(
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.total_profit), 0),
            )
            .filter(
                Sale.user_id == current_user.id,
                Sale.created_at >= day,
                Sale.created_at < next_day,
            )
            .one()
        )
        last_7_days.append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "total_amount": float(total),
                "total_profit": float(profit),
            }
        )

    return jsonify(
        {
            "success": True,
            "data": {
                "today": {
                    "total_amount": float(today_total),
                    "total_profit": float(today_profit),
                    "sale_count": int(today_count),
                },
                "month": {
                    "total_amount": float(month_total),
                    "total_profit": float(month_profit),
                    "sale_count": int(month_count),
                },
                "stock": {
                    "total_products": int(total_products),
                    "total_units": int(total_units),
                    "stock_value": float(stock_value),
                    "threshold": low_threshold,
                    "low_stock_count": len(low_stock),
                    "out_of_stock_count": len(out_of_stock_items),
                    "low_only_count": len(low_items),
                    "low_stock_items": [p.to_dict(threshold=low_threshold) for p in low_stock],
                    "out_of_stock": [p.to_dict(threshold=low_threshold) for p in out_of_stock_items],
                    "low": [p.to_dict(threshold=low_threshold) for p in low_items],
                },
                "last_7_days": last_7_days,
            },
        }
    )


@bp.get("/reports/profit")
@login_required
def profit_report():
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    daily = []
    for i in range(29, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)
        total, profit = (
            db.session.query(
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.total_profit), 0),
            )
            .filter(
                Sale.user_id == current_user.id,
                Sale.created_at >= day,
                Sale.created_at < next_day,
            )
            .one()
        )
        daily.append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "total_amount": float(total),
                "total_profit": float(profit),
            }
        )

    return jsonify({"success": True, "data": {"daily": daily}})


@bp.get("/reports/stock")
@login_required
def stock_report():
    products = (
        Product.query.filter_by(user_id=current_user.id).order_by(Product.quantity).all()
    )
    total_value = sum(float(p.cost_price) * p.quantity for p in products)
    low_stock = [p for p in products if p.quantity <= 5]
    return jsonify(
        {
            "success": True,
            "data": {
                "total_items": len(products),
                "total_units": sum(p.quantity for p in products),
                "total_value": total_value,
                "low_stock": [p.to_dict() for p in low_stock],
                "products": [p.to_dict() for p in products],
            },
        }
    )
