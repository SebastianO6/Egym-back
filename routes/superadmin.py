from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import Gym, User
from routes.decorators import role_required
from utils.mailer import send_gymadmin_invite_email
import secrets
from datetime import datetime, timedelta
import string



superadmin_bp = Blueprint(
    "superadmin",
    __name__,
)

def generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ---------------- GYMS ----------------
@superadmin_bp.get("/gyms")
@jwt_required()
@role_required("superadmin")
def get_gyms():
    gyms = Gym.query.all()
    data = []

    for gym in gyms:
        members = User.query.filter_by(
            gym_id=gym.id,
            role="client",
            is_active=True
        ).count()

        admin = User.query.filter_by(
            gym_id=gym.id,
            role="gymadmin"
        ).first()

        data.append({
            "id": gym.id,
            "name": gym.name,
            "address": gym.address or "",
            "phone": gym.phone or "",
            "owner_email": admin.email if admin else None,
            "members": members,
            "monthly_revenue_ksh": members * 300
        })

    return jsonify(data), 200



@superadmin_bp.post("/gyms")
@jwt_required()
@role_required("superadmin")
def create_gym():
    data = request.get_json() or {}

    name = data.get("name")
    owner_email = data.get("owner_email")

    if not name or not owner_email:
        return {"error": "Gym name and owner email required"}, 400

    if Gym.query.filter_by(name=name).first():
        return {"error": "Gym already exists"}, 409

    if User.query.filter_by(email=owner_email).first():
        return {"error": "Email already in use"}, 409

    # 1️⃣ Create gym
    gym = Gym(
        name=name,
        phone=data.get("phone"),
        address=data.get("address")
    )
    db.session.add(gym)
    db.session.flush()  # get gym.id safely

    # 2️⃣ Create gymadmin (INACTIVE)
    token = secrets.token_urlsafe(32)

    admin = User(
        email=owner_email,
        role="gymadmin",
        gym_id=gym.id,
        is_active=False,
        password_hash=None,
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.session.add(admin)
    db.session.commit()

    # 3️⃣ Send invite email
    send_gymadmin_invite_email(
        email=admin.email,
        gym_name=gym.name,
        token=token
    )

    return {
        "message": "Gym created. Invite sent to gym admin."
    }, 201




# ---------------- REVENUE ----------------
@superadmin_bp.get("/revenue")
@jwt_required()
@role_required("superadmin")
def platform_revenue():
    gyms = Gym.query.all()

    total = 0
    rows = []

    for gym in gyms:
        members = User.query.filter_by(
            gym_id=gym.id,
            role="client",
            is_active=True
        ).count()

        revenue = members * 300
        total += revenue

        rows.append({
            "gym_id": gym.id,
            "gym_name": gym.name,
            "members": members,
            "revenue_ksh": revenue
        })

    return jsonify({
        "currency": "KES",
        "total_revenue": total,
        "gyms": rows
    }), 200



# ---------------- USERS ----------------
@superadmin_bp.get("/users")
@jwt_required()
@role_required("superadmin")
def get_all_users():
    users = User.query.all()

    return jsonify([
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "gym_id": u.gym_id,
            "gym_name": u.gym.name if u.gym else None,
            "is_active": u.is_active
        }
        for u in users
    ])



@superadmin_bp.delete("/gyms/<int:gym_id>")
@jwt_required()
@role_required("superadmin")
def delete_gym(gym_id):
    gym = Gym.query.get_or_404(gym_id)
    db.session.delete(gym)
    db.session.commit()
    return jsonify({"message": "Gym deleted"}), 200






