from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from extensions import db
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---------------- LOGIN ----------------
@auth_bp.post("/login")
def login():
    data = request.get_json()

    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    # ✅ IMPORTANT: identity = user.id
    # ✅ IMPORTANT: role added to JWT claims
    access_token = create_access_token(
        identity=user.id,
        additional_claims={
            "role": user.role,
            "gym_id": user.gym_id
        }
    )

    refresh_token = create_refresh_token(
        identity=user.id
    )

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "gym_id": user.gym_id,
            "must_change_password": user.must_change_password
        }
    }), 200


# ---------------- CURRENT USER ----------------
@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get_or_404(get_jwt_identity())

    return jsonify({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "gym_id": user.gym_id
    }), 200
