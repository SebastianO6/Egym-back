from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from models import User
from extensions import db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.post("/login")
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))  # FIXED

    return jsonify({
        "access_token": token,
        "refresh_token": "dummy",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "gym_id": user.gym_id,
            "must_change_password": user.must_change_password
        },
        "must_change_password": user.must_change_password
    })
