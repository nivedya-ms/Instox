from datetime import datetime

from ..database.db import db


class PurchaseListItem(db.Model):
    __tablename__ = "purchase_lists"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    is_purchased = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "is_purchased": self.is_purchased,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
