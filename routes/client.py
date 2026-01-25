from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from routes.decorators import role_required
from models import WorkoutPlan, Payment, Subscription, Announcement, User

client_bp = Blueprint("client", __name__)

# -------- WORKOUT PLANS --------
@client_bp.get("/plans")
@jwt_required()
@role_required("client")
def get_my_plans():
    user_id = get_jwt_identity()

    plans = WorkoutPlan.query.filter_by(client_id=user_id).all()

    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "duration": p.duration,
            "exercises": p.exercises
        }
        for p in plans
    ])


# -------- PAYMENTS --------
@client_bp.get("/payments")
@jwt_required()
@role_required("client")
def my_payments():
    user_id = get_jwt_identity()

    payments = Payment.query.filter_by(user_id=user_id).order_by(
        Payment.created_at.desc()
    ).all()

    return jsonify({
        "items": [
            {
                "id": p.id,
                "amount": float(p.amount),
                "method": p.method,
                "status": p.status,
                "created_at": p.created_at
            }
            for p in payments
        ]
    })


# -------- SUBSCRIPTION --------
@client_bp.get("/subscription")
@jwt_required()
@role_required("client")
def my_subscription():
    user_id = get_jwt_identity()

    sub = Subscription.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()

    return {
        "active": bool(sub),
        "plan": sub.plan_name if sub else None,
        "start_date": sub.start_date if sub else None,
        "end_date": sub.end_date if sub else None
    }


# -------- ANNOUNCEMENTS --------
@client_bp.get("/announcements")
@jwt_required()
@role_required("client")
def client_announcements():
    user = User.query.get(get_jwt_identity())

    announcements = Announcement.query.filter_by(
        gym_id=user.gym_id
    ).order_by(Announcement.created_at.desc()).all()

    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at
        }
        for a in announcements
    ])


@client_bp.get("/membership/me")
@jwt_required()
@role_required("client")
def my_membership():
    user_id = get_jwt_identity()

    sub = Subscription.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(Subscription.end_date.desc()).first()

    if not sub:
        return jsonify({"expired": True})

    return jsonify({
        "due_date": sub.end_date.date().isoformat(),
        "expired": sub.end_date < datetime.utcnow()
    })