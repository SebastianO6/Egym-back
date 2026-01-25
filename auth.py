from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from datetime import timedelta, datetime
from extensions import db
from models.user import User
from routes.decorators import password_change_only, block_temp_tokens
from werkzeug.security import generate_password_hash


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---------------- LOGIN ----------------
@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return {"error": "Invalid credentials"}, 401

    if user.invite_token:
        return {"error": "Account not activated"}, 403

    if not user.is_active:
        return {"error": "Account disabled"}, 403

    claims = {
        "role": user.role,
        "gym_id": user.gym_id,
        "pwd_change_only": user.must_change_password
    }

    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id))

    

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }, 200



# ---------------- CURRENT USER ----------------
@auth_bp.get("/me")
@jwt_required()
@block_temp_tokens
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


# ---------------- FORCE PASSWORD CHANGE ----------------
@auth_bp.put("/force-change-password")
@jwt_required()
@password_change_only
def force_change_password():
    data = request.get_json() or {}
    new_password = data.get("new_password")

    if not new_password:
        return jsonify({"error": "New password required"}), 400

    user = User.query.get_or_404(int(get_jwt_identity()))

    if not user.must_change_password:
        return jsonify({"error": "Password change not required"}), 400

    user.set_password(new_password)
    user.must_change_password = False
    db.session.commit()

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "gym_id": user.gym_id,
            "pwd_change_only": False   # ✅ REQUIRED
        }
    )


    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "success": True,
        "message": "Password changed successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200


@auth_bp.post("/accept-invite")
def accept_invite():
    data = request.get_json() or {}
    token = data.get("token")
    password = data.get("password")

    if not token or not password:
        return {"msg": "Token and password required"}, 400

    user = User.query.filter_by(invite_token=token).first()

    if not user:
        return {"msg": "Invite invalid or expired"}, 400

    if not user.invite_expires_at or user.invite_expires_at < datetime.utcnow():
        return {"msg": "Invite invalid or expired"}, 400

    user.set_password(password)
    user.is_active = True
    user.invite_token = None
    user.invite_expires_at = None
    user.must_change_password = False

    db.session.commit()

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "gym_id": user.gym_id,
            "pwd_change_only": False   # ✅ REQUIRED
        }
    )


    return {
        "access_token": access_token,
        "user": user.to_dict()
    }, 200








