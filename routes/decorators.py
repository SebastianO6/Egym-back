from flask_jwt_extended import get_jwt_identity
from functools import wraps
from flask import jsonify
from models import User

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user = User.query.get(get_jwt_identity())
            if not user or user.role not in roles:
                return jsonify({"error": "Unauthorized"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
