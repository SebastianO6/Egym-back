from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS

from config import Config
from extensions import db, jwt, mail, migrate, socketio
from utils.scheduler import start_scheduler


def _allowed_origins(frontend_url):
    origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }

    if frontend_url:
        origins.update(
            origin.strip()
            for origin in frontend_url.split(",")
            if origin.strip()
        )

    return sorted(origins)


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)
    allowed_origins = _allowed_origins(app.config.get("FRONTEND_URL"))

    mail.init_app(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    db.init_app(app)
    import models  # noqa: F401

    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins=allowed_origins)

    from auth import auth_bp
    from routes.announcements import announcements_bp
    from routes.client import client_bp
    from routes.gymadmin import gymadmin_bp
    from routes.messages import messages_bp
    from routes.schedules import schedules_bp
    from routes.superadmin import superadmin_bp
    from routes.trainer import trainer_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")
    app.register_blueprint(gymadmin_bp, url_prefix="/api/gymadmin")
    app.register_blueprint(trainer_bp, url_prefix="/api/trainer")
    app.register_blueprint(client_bp, url_prefix="/api/client")
    app.register_blueprint(messages_bp, url_prefix="/api/messages")
    app.register_blueprint(schedules_bp, url_prefix="/api/schedules")
    app.register_blueprint(announcements_bp)

    from sockets import chat  # noqa: F401

    @app.after_request
    def add_cors_headers(response):
        request_origin = request.headers.get("Origin")
        origin = request_origin if request_origin in allowed_origins else None

        if not origin and allowed_origins:
            origin = allowed_origins[0]

        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"

        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    with app.app_context():
        start_scheduler(app)

    return app
