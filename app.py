import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from extensions import db, migrate, jwt, mail, socketio
from config import Config
from utils.scheduler import start_scheduler



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mail.init_app(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app)  # ✅ IMPORTANT
    load_dotenv()

    from auth import auth_bp
    from routes.superadmin import superadmin_bp
    from routes.gymadmin import gymadmin_bp
    from routes.trainer import trainer_bp
    from routes.client import client_bp
    from routes.messages import messages_bp
    from routes.schedules import schedules_bp
    from routes.announcements import announcements_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")
    app.register_blueprint(gymadmin_bp, url_prefix="/api/gymadmin")
    app.register_blueprint(trainer_bp, url_prefix="/api/trainer")
    app.register_blueprint(client_bp, url_prefix="/api/client")
    app.register_blueprint(messages_bp, url_prefix="/api/messages")
    app.register_blueprint(schedules_bp, url_prefix="/api/schedules")
    app.register_blueprint(announcements_bp)

    # ✅ Import sockets AFTER everything initialized
    from sockets import chat

    with app.app_context():
        start_scheduler(app)

    return app