from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..database.db import db
from ..models.purchase_list import PurchaseListItem

bp = Blueprint("purchase_list", __name__)


@bp.get("")
@login_required
def list_items():
    items = (
        PurchaseListItem.query.filter_by(user_id=current_user.id)
        .order_by(PurchaseListItem.is_purchased, PurchaseListItem.created_at.desc())
        .all()
    )
    return jsonify({"success": True, "data": [i.to_dict() for i in items]})


@bp.post("")
@login_required
def add_item():
    data = request.get_json(silent=True) or {}
    name = (data.get("item_name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "item_name is required"}), 400
    try:
        qty = int(data.get("quantity", 1))
        if qty <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "quantity must be a positive integer"}), 400
    item = PurchaseListItem(user_id=current_user.id, item_name=name, quantity=qty)
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "data": item.to_dict()}), 201


@bp.put("/<int:item_id>")
@login_required
def update_item(item_id):
    item = PurchaseListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item is None:
        return jsonify({"success": False, "error": "Item not found"}), 404
    data = request.get_json(silent=True) or {}
    if "is_purchased" in data:
        item.is_purchased = bool(data["is_purchased"])
    if "item_name" in data:
        name = (data.get("item_name") or "").strip()
        if not name:
            return jsonify({"success": False, "error": "item_name cannot be empty"}), 400
        item.item_name = name
    if "quantity" in data:
        try:
            qty = int(data["quantity"])
            if qty <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "quantity must be a positive integer"}), 400
        item.quantity = qty
    db.session.commit()
    return jsonify({"success": True, "data": item.to_dict()})


@bp.delete("/<int:item_id>")
@login_required
def delete_item(item_id):
    item = PurchaseListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item is None:
        return jsonify({"success": False, "error": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True})
