from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method == "OPTIONS":
                return "", 200

            verify_jwt_in_request()
            claims = get_jwt()

            # Block temp-password tokens
            if claims.get("pwd_change_only", False):
                return jsonify({"error": "Password change required"}), 403

            if claims.get("role") not in allowed_roles:
                return jsonify({"error": "Unauthorized"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def password_change_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()

        if not claims.get("pwd_change_only", False):
            return jsonify({"error": "Invalid or expired temporary token"}), 403

        return fn(*args, **kwargs)
    return wrapper


def block_temp_tokens(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()

        if claims.get("pwd_change_only", False):
            return jsonify({"error": "Password change required"}), 403

        return fn(*args, **kwargs)
    return wrapper


def gym_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()

        if not claims.get("gym_id"):
            return jsonify({"error": "Gym context required"}), 403

        return fn(*args, **kwargs)
    return wrapper





