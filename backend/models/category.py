from datetime import datetime

from ..database.db import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), default="pieces", nullable=False)
    icon = db.Column(db.String(8), default="📦", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "unit": self.unit or "pieces",
            "icon": self.icon or "📦",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Starter categories seeded on user registration. Ordered by likelihood for
# a small textile/footwear shop in Kerala. Owner can rename/delete freely.
DEFAULT_CATEGORIES = [
    {"name": "Curtains", "unit": "pieces", "icon": "🪟"},
    {"name": "Running Material", "unit": "meters", "icon": "🧵"},
    {"name": "Footwear", "unit": "pairs", "icon": "👟"},
    {"name": "Sarees", "unit": "pieces", "icon": "🥻"},
    {"name": "Blouses", "unit": "pieces", "icon": "👚"},
    {"name": "Home Textiles", "unit": "pieces", "icon": "🛏️"},
    {"name": "Accessories", "unit": "pieces", "icon": "🎀"},
    {"name": "Other", "unit": "pieces", "icon": "📦"},
]
