import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instox.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_PROFIT_PERCENTAGE = 30.0
    LOW_STOCK_THRESHOLD = 5
    JSON_SORT_KEYS = False
    UPLOAD_FOLDER = str(BASE_DIR / "backend" / "uploads")
    ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per upload


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    UPLOAD_FOLDER = str(BASE_DIR / "backend" / "uploads_test")
