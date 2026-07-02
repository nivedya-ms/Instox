from datetime import datetime

from ..database.db import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    cost_price = db.Column(db.Numeric(10, 2), nullable=False)
    retail_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    sku = db.Column(db.String(50))
    unique_id = db.Column(db.String(20), unique=True, index=True)
    photo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def format_unique_id(row_id):
        return f"INSTOX-{row_id:05d}"

    category = db.relationship("Category", backref="products")

    def stock_status(self, threshold=5):
        if self.quantity <= 0:
            return "out_of_stock"
        if self.quantity <= threshold:
            return "low"
        return "normal"

    def to_dict(self, include_cost=True, threshold=5):
        data = {
            "id": self.id,
            "unique_id": self.unique_id or (self.format_unique_id(self.id) if self.id else None),
            "name": self.name,
            "description": self.description,
            "retail_price": float(self.retail_price),
            "quantity": self.quantity,
            "sku": self.sku,
            "photo_url": self.photo_url,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "in_stock": self.quantity > 0,
            "stock_status": self.stock_status(threshold),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_cost:
            data["cost_price"] = float(self.cost_price)
            data["profit_per_unit"] = float(self.retail_price) - float(self.cost_price)
        return data
