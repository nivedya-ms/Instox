from datetime import datetime

from ..database.db import db


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    customer_name = db.Column(db.String(100))
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    total_profit = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    items = db.relationship(
        "SaleItem", backref="sale", cascade="all, delete-orphan", lazy="joined"
    )

    def to_dict(self, include_profit=True, include_items=True):
        data = {
            "id": self.id,
            "customer_name": self.customer_name,
            "total_amount": float(self.total_amount),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_profit:
            data["total_profit"] = float(self.total_profit)
        if include_items:
            data["items"] = [i.to_dict(include_profit=include_profit) for i in self.items]
        return data


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    profit = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship("Product")

    def to_dict(self, include_profit=True):
        data = {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "subtotal": float(self.unit_price) * self.quantity,
        }
        if include_profit:
            data["unit_cost"] = float(self.unit_cost)
            data["profit"] = float(self.profit)
        return data
