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

    # LLM — generic OpenAI-compatible client. Set LLM_BASE_URL to point at any
    # provider (DeepSeek, Qwen/DashScope, Zhipu, OpenAI, local vLLM, ...).
    # LLM_PROVIDER='stub' short-circuits network calls with canned responses.
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "stub").lower()
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

    # Vision — falls back to LLM_* if the VISION_* variants are unset. Different
    # providers use different vision-capable model names (qwen-vl-plus,
    # glm-4v, gpt-4o, gemini-1.5-flash, ...).
    VISION_API_KEY = os.environ.get("VISION_API_KEY", "")
    VISION_BASE_URL = os.environ.get("VISION_BASE_URL", "")
    VISION_MODEL = os.environ.get("VISION_MODEL", "qwen-vl-plus")

    SQL_MAX_ROWS = 100
    SQL_TIMEOUT_MS = 3000

    # Photo-to-cart matching thresholds.
    IDENTIFY_AUTO_PICK_CONFIDENCE = 0.85
    IDENTIFY_MAX_ITEMS = 8
    IDENTIFY_MAX_CANDIDATES = 3


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    UPLOAD_FOLDER = str(BASE_DIR / "backend" / "uploads_test")
    LLM_PROVIDER = "stub"
