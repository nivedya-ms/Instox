from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..database.db import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    shop_name = db.Column(db.String(100))
    profit_percentage = db.Column(db.Numeric(5, 2), default=30.00, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=5, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "shop_name": self.shop_name,
            "profit_percentage": float(self.profit_percentage),
            "low_stock_threshold": int(self.low_stock_threshold),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
