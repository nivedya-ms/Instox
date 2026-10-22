from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..database.db import db
from ..models.category import Category
from ..models.product import Product

bp = Blueprint("categories", __name__)


@bp.get("")
@login_required
def list_categories():
    cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return jsonify({"success": True, "data": [c.to_dict() for c in cats]})


@bp.post("")
@login_required
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    unit = (data.get("unit") or "pieces").strip() or "pieces"
    icon = (data.get("icon") or "📦").strip() or "📦"
    cat = Category(
        user_id=current_user.id,
        name=name,
        description=(data.get("description") or "").strip() or None,
        unit=unit,
        icon=icon,
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify({"success": True, "data": cat.to_dict()}), 201


@bp.put("/<int:cat_id>")
@login_required
def update_category(cat_id):
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first()
    if cat is None:
        return jsonify({"success": False, "error": "Category not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"success": False, "error": "Name cannot be empty"}), 400
        cat.name = name
    if "description" in data:
        cat.description = (data.get("description") or "").strip() or None
    if "unit" in data:
        cat.unit = (data.get("unit") or "pieces").strip() or "pieces"
    if "icon" in data:
        cat.icon = (data.get("icon") or "📦").strip() or "📦"
    db.session.commit()
    return jsonify({"success": True, "data": cat.to_dict()})


@bp.delete("/<int:cat_id>")
@login_required
def delete_category(cat_id):
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first()
    if cat is None:
        return jsonify({"success": False, "error": "Category not found"}), 404
    Product.query.filter_by(user_id=current_user.id, category_id=cat_id).update(
        {"category_id": None}
    )
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"success": True})
