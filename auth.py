from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from datetime import timedelta, datetime
from extensions import db
from models.user import User
from models.gym_subscription import GymSubscription
from routes.decorators import password_change_only, block_temp_tokens
from werkzeug.security import generate_password_hash
from models.gym import Gym
from utils.audit import log_action
import secrets


auth_bp = Blueprint("auth", __name__)  # ✅ NO url_prefix here

def build_join_url(slug):
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{frontend_url}/join/{slug}"


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    if not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    # ✅ BLOCK INACTIVE USERS
    if not user.is_active:
        return jsonify({
            "message": "Account inactive. Contact gym administration."
        }), 403
    
    if user.gym and user.gym.status != "active":
        return jsonify({
            "message": "Gym subscription inactive. Contact platform support."
        }), 403

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "gym_id": user.gym_id
        }
    )

    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200

# ---------------- CURRENT USER ----------------
@auth_bp.get("/me")
@jwt_required()
@block_temp_tokens
def me():

    user = db.session.get(User, int(get_jwt_identity()))

    if not user:
        return jsonify({"error": "User not found"}), 404

    # 🚨 User manually disabled
    if not user.is_active:
        return jsonify({"error": "Account inactive"}), 403

    # 🚨 Gym manually disabled
    if user.gym and user.gym.status != "active":
        return jsonify({"error": "Gym inactive"}), 403

    # 🚨 Check subscription expiry
    if user.gym:
        sub = (
            GymSubscription.query
            .filter_by(gym_id=user.gym_id)
            .order_by(GymSubscription.end_date.desc())
            .first()
        )

        if not sub or sub.end_date < datetime.utcnow():
            return jsonify({"error": "Gym subscription expired"}), 403

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
        return jsonify({"error": "Token and password are required"}), 400

    user = User.query.filter_by(invite_token=token).first()

    if not user:
        return jsonify({"error": "Invalid or expired invite"}), 400

    if not user.invite_expires_at or user.invite_expires_at < datetime.utcnow():
        return jsonify({"error": "Invite has expired"}), 400

    if user.is_active:
        return jsonify({"error": "Invite already used"}), 400

    user.set_password(password)
    user.is_active = True
    user.must_change_password = False

    user.invite_token = None
    user.invite_expires_at = None

    db.session.commit()

    return jsonify({
        "message": "Account activated successfully",
        "role": user.role
    }), 200


@auth_bp.put("/change-password")
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    user = User.query.get(user_id)

    if not user or not user.check_password(current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200


@auth_bp.post("/register")
def register():

    data = request.get_json()

    gym_slug = data.get("gym_slug")
    email = data.get("email")

    gym = Gym.query.filter_by(slug=gym_slug).first()

    if not gym:
        return jsonify({"error": "Invalid gym"}), 404

    if gym.status != "active":
        return jsonify({"error": "Gym is not accepting registrations"}), 403

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 400

    token = secrets.token_urlsafe(32)

    user = User(
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        email=email,
        phone=data.get("phone"),
        role="client",
        gym_id=gym.id,
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24),
        is_active=False
    )

    db.session.add(user)
    db.session.commit()
    log_action(
        action="member_self_registered",
        entity="user",
        entity_id=user.id,
        details={
            "email": user.email,
            "gym_id": gym.id,
            "gym_slug": gym.slug,
        },
        commit=True,
    )

    return jsonify({
        "activation_token": token
    }), 201


@auth_bp.get("/gyms/<string:gym_slug>")
def get_gym_by_slug(gym_slug):
    gym = Gym.query.filter_by(slug=gym_slug).first()

    if not gym:
        return jsonify({"error": "Invalid gym"}), 404

    if gym.status != "active":
        return jsonify({"error": "Gym is not accepting registrations"}), 403

    return jsonify({
        "id": gym.id,
        "name": gym.name,
        "slug": gym.slug,
        "status": gym.status,
        "join_url": build_join_url(gym.slug),
    }), 200
