import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from .config import Config
from .database.db import db

login_manager = LoginManager()
login_manager.login_view = None


def create_app(config_class=Config):
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="/static",
        template_folder=str(frontend_dir),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, supports_credentials=True)
    login_manager.init_app(app)

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    from .routes.auth import bp as auth_bp
    from .routes.products import bp as products_bp
    from .routes.sales import bp as sales_bp
    from .routes.purchase_list import bp as purchase_bp
    from .routes.categories import bp as categories_bp
    from .routes.dashboard import bp as dashboard_bp
    from .routes.settings import bp as settings_bp
    from .routes.ai import bp as ai_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(sales_bp, url_prefix="/api/sales")
    app.register_blueprint(purchase_bp, url_prefix="/api/purchase-list")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(ai_bp, url_prefix="/api/ai")

    @app.errorhandler(404)
    def not_found(e):
        if (str(e.description) if hasattr(e, "description") else "").startswith("API"):
            return jsonify({"success": False, "error": "Not found"}), 404
        return jsonify({"success": False, "error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<page>.html")
    def page(page):
        return send_from_directory(frontend_dir, f"{page}.html")

    @app.route("/sw.js")
    def service_worker():
        return send_from_directory(frontend_dir, "sw.js")

    @app.route("/manifest.json")
    def pwa_manifest():
        return send_from_directory(frontend_dir, "manifest.json")

    upload_dir = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(upload_dir, filename)

    with app.app_context():
        db.create_all()
        _apply_lightweight_migrations()

    # Prefetch MobileCLIP in the background so first request is fast. In
    # testing (or if the user disables), skip.
    if not app.config.get("TESTING") and not app.config.get("DISABLE_MOBILECLIP_WARMUP"):
        from .services import mobileclip
        mobileclip.warmup_async()

    return app


def _apply_lightweight_migrations():
    """Add columns missing from existing tables. Idempotent."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "low_stock_threshold" not in user_cols:
            with db.engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN low_stock_threshold INTEGER NOT NULL DEFAULT 5"
                    )
                )

    if "products" in tables:
        product_cols = {c["name"] for c in inspector.get_columns("products")}
        with db.engine.begin() as conn:
            if "unique_id" not in product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN unique_id VARCHAR(20)"))
                conn.execute(
                    text(
                        "UPDATE products SET unique_id = 'INSTOX-' || substr('00000' || id, -5, 5) "
                        "WHERE unique_id IS NULL"
                    )
                )
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_products_unique_id "
                        "ON products(unique_id)"
                    )
                )
            if "photo_url" not in product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN photo_url VARCHAR(255)"))
            if "photo_embedding" not in product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN photo_embedding BLOB"))
            if "photo_embedded_at" not in product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN photo_embedded_at TIMESTAMP"))

    if "categories" in tables:
        cat_cols = {c["name"] for c in inspector.get_columns("categories")}
        with db.engine.begin() as conn:
            if "unit" not in cat_cols:
                conn.execute(
                    text("ALTER TABLE categories ADD COLUMN unit VARCHAR(20) NOT NULL DEFAULT 'pieces'")
                )
            if "icon" not in cat_cols:
                conn.execute(
                    text("ALTER TABLE categories ADD COLUMN icon VARCHAR(8) NOT NULL DEFAULT '📦'")
                )
