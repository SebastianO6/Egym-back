import os

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO(
    async_mode=os.getenv("SOCKET_ASYNC_MODE", "threading"),
    cors_allowed_origins="*",
)

# Always store identity as string
@jwt.user_identity_loader
def user_identity_lookup(identity):
    return str(identity)
