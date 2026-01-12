from flask import Blueprint, jsonify
from extensions import db
from models import Gym, Payment
from decorators import role_required
from sqlalchemy import func
    
superadmin_bp = Blueprint("superadmin", __name__)

@superadmin_bp.get("/superadmin/gyms")
@role_required("superadmin")
def gyms():
    gyms = Gym.query.all()
    return jsonify([
        {"id": g.id, "name": g.name}
        for g in gyms
    ])

@superadmin_bp.get("/superadmin/revenue")
@role_required("superadmin")
def revenue():
    total = db.session.query(func.sum(Payment.amount)).scalar() or 0
    return jsonify({"total": total})
