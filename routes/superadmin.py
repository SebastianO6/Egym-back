from flask import Blueprint, jsonify, request
from extensions import db
from models import Gym, Payment
from sqlalchemy import func

superadmin_bp = Blueprint("superadmin", __name__, url_prefix="/superadmin")


@superadmin_bp.get("/gyms")
def get_gyms():
    gyms = Gym.query.all()
    return jsonify([
        {"id": g.id, "name": g.name, "location": g.location}
        for g in gyms
    ])


@superadmin_bp.post("/gyms")
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
def revenue():
    data = (
        Payment.query
        .with_entities(Payment.gym_id, func.sum(Payment.amount))
        .group_by(Payment.gym_id)
        .all()
    )
    return jsonify([{ "gym_id": g, "revenue": float(r)} for g, r in data])
