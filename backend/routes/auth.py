import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..database.db import db
from ..models.category import DEFAULT_CATEGORIES, Category
from ..models.user import User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    shop_name = (data.get("shop_name") or "").strip() or None

    if not username or not email or not password:
        return jsonify({"success": False, "error": "username, email, password required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "Invalid email"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    user = User(username=username, email=email, shop_name=shop_name)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
        for spec in DEFAULT_CATEGORIES:
            db.session.add(
                Category(user_id=user.id, name=spec["name"], unit=spec["unit"], icon=spec["icon"])
            )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "error": "Username or email already exists"}), 409

    login_user(user)
    return jsonify({"success": True, "data": user.to_dict()}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    login_user(user)
    return jsonify({"success": True, "data": user.to_dict()})


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})


@bp.get("/me")
@login_required
def me():
    return jsonify({"success": True, "data": current_user.to_dict()})


@bp.put("/me")
@login_required
def update_me():
    data = request.get_json(silent=True) or {}
    if "shop_name" in data:
        current_user.shop_name = (data.get("shop_name") or "").strip() or None
    if "profit_percentage" in data:
        try:
            pct = float(data["profit_percentage"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid profit_percentage"}), 400
        if pct < 0 or pct > 1000:
            return jsonify({"success": False, "error": "profit_percentage out of range"}), 400
        current_user.profit_percentage = pct
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
    db.session.commit()
    return jsonify({"success": True, "data": current_user.to_dict()})
