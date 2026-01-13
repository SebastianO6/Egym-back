from flask import Flask
from extensions import db, migrate
from config import Config
from flask_cors import CORS


from routes.gymadmin import gymadmin_bp
from routes.trainer import trainer_bp
from routes.client import client_bp
from routes.messages import messages_bp
from routes.superadmin import superadmin_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True)


    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(gymadmin_bp)
    app.register_blueprint(trainer_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(superadmin_bp)

    return app

app = create_app()
