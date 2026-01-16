from flask import Flask
from flask_cors import CORS
from extensions import db, migrate, jwt
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ VERY IMPORTANT
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"]
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from auth import auth_bp
    from routes.superadmin import superadmin_bp
    from routes.gymadmin import gymadmin_bp
    from routes.trainer import trainer_bp
    from routes.client import client_bp
    from routes.messages import messages_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")
    app.register_blueprint(gymadmin_bp, url_prefix="/api/gymadmin")
    app.register_blueprint(trainer_bp, url_prefix="/api/trainer")
    app.register_blueprint(client_bp, url_prefix="/api/client")
    app.register_blueprint(messages_bp)

    return app
