from flask import Blueprint, jsonify, request
from extensions import db
from models import Gym, User
from flask_jwt_extended import jwt_required
from routes.decorators import role_required

superadmin_bp = Blueprint(
    "superadmin",
    __name__,
    url_prefix="/api/superadmin"
)


@superadmin_bp.get("/gyms")
@jwt_required()
@role_required("superadmin")
def get_gyms():
    gyms = Gym.query.all()
    return jsonify([
        {"id": g.id, "name": g.name, "location": g.location}
        for g in gyms
    ])


@superadmin_bp.post("/gyms")
@jwt_required()
@role_required("superadmin")
def create_gym():
    data = request.get_json()

    gym = Gym(
        name=data["name"],
        location=data.get("location"),
    )
    db.session.add(gym)
    db.session.commit()

    return jsonify({"msg": "Gym created"}), 201


@superadmin_bp.get("/revenue")
@jwt_required()
@role_required("superadmin")
def platform_revenue():
    return jsonify({
        "total_platform_revenue": 0,
        "per_gym": []
    })


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
            "is_active": u.is_active
        }
        for u in users
    ])
