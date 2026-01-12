from flask import Flask
from flask_jwt_extended import JWTManager

from extensions import db, migrate
from models import *

# blueprints
from auth import auth_bp
from routes.gymadmin import gymadmin_bp
from routes.superadmin import superadmin_bp
from routes.trainer import trainer_bp
from routes.client import client_bp
from routes.messages import messages_bp


def create_app():
    app = Flask(__name__)

    # ---------------- CONFIG ----------------
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql://egym_user:pass12word@localhost/egymdb"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "change-this-in-production"

    # ---------------- INIT ----------------
    db.init_app(app)
    migrate.init_app(app, db)
    JWTManager(app)

    # ---------------- ROUTES ----------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(gymadmin_bp)
    app.register_blueprint(trainer_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(messages_bp)

    return app


app = create_app()

# ---------------- SEED COMMAND ----------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        with app.app_context():
            from seed import seed
            seed()
    else:
        app.run(debug=True)
