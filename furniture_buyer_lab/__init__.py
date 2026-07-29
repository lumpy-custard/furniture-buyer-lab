from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()

    from .auth import auth_bp
    from .main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    from .catalog_sync import register_cli
    register_cli(app)

    from .product_art import product_sketch
    app.jinja_env.globals["product_sketch"] = product_sketch

    from .product_photos import sketch_image_url
    app.jinja_env.globals["product_sketch_image"] = sketch_image_url

    @app.context_processor
    def inject_cart_item_count():
        from .cart import cart_item_count

        if not current_user.is_authenticated:
            return {"cart_item_count": 0}
        return {"cart_item_count": cart_item_count()}

    @app.context_processor
    def inject_nav_balance():
        import os
        from .external_api import ExternalAPIError, get_balance

        if not current_user.is_authenticated:
            return {"nav_balance": None}
        user_id = os.environ.get("FURNITURE_API_USER_ID", "").strip()
        if not user_id:
            return {"nav_balance": None}
        try:
            return {"nav_balance": get_balance(user_id).get("balance")}
        except ExternalAPIError:
            return {"nav_balance": None}

    return app
