from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..database.db import db

bp = Blueprint("settings", __name__)


def _settings_dict():
    return {
        "low_stock_threshold": int(current_user.low_stock_threshold),
        "profit_percentage": float(current_user.profit_percentage),
        "shop_name": current_user.shop_name,
    }


@bp.get("")
@login_required
def get_settings():
    return jsonify({"success": True, "data": _settings_dict()})


@bp.put("")
@login_required
def update_settings():
    data = request.get_json(silent=True) or {}
    if "low_stock_threshold" in data:
        try:
            v = int(data["low_stock_threshold"])
            if v < 0:
                raise ValueError
        except (TypeError, ValueError):
            return (
                jsonify({"success": False, "error": "low_stock_threshold must be a non-negative integer"}),
                400,
            )
        current_user.low_stock_threshold = v
    if "profit_percentage" in data:
        try:
            pct = float(data["profit_percentage"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid profit_percentage"}), 400
        if pct < 0 or pct > 1000:
            return jsonify({"success": False, "error": "profit_percentage out of range"}), 400
        current_user.profit_percentage = pct
    if "shop_name" in data:
        current_user.shop_name = (data.get("shop_name") or "").strip() or None
    db.session.commit()
    return jsonify({"success": True, "data": _settings_dict()})


@bp.put("/threshold")
@login_required
def update_threshold():
    data = request.get_json(silent=True) or {}
    raw = data.get("low_stock_threshold", data.get("threshold"))
    try:
        v = int(raw)
        if v < 0:
            raise ValueError
    except (TypeError, ValueError):
        return (
            jsonify({"success": False, "error": "low_stock_threshold must be a non-negative integer"}),
            400,
        )
    current_user.low_stock_threshold = v
    db.session.commit()
    return jsonify({"success": True, "data": _settings_dict()})
