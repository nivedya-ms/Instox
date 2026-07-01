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

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(sales_bp, url_prefix="/api/sales")
    app.register_blueprint(purchase_bp, url_prefix="/api/purchase-list")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(dashboard_bp, url_prefix="/api")

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

    with app.app_context():
        db.create_all()

    return app
