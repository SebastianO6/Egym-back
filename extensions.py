from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

# ✅ ADD THIS
@jwt.user_identity_loader
def user_identity_lookup(identity):
    # Always store identity as string
    return str(identity)
