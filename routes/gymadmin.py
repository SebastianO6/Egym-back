from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User, Announcement
from routes.decorators import role_required

gymadmin_bp = Blueprint("gymadmin", __name__)

# -------- MEMBERS --------
@gymadmin_bp.get("/members")
@jwt_required()
@role_required("gymadmin")
def members():
    admin = User.query.get_or_404(get_jwt_identity())

    clients = User.query.filter_by(
        gym_id=admin.gym_id,
        role="client"
    ).all()

    return jsonify({
        "items": [
            {
                "id": c.id,
                "name": c.full_name,
                "email": c.email,
                "plan": c.subscription_plan,
                "status": c.payment_status,
                "dueDate": c.payment_due_date.isoformat() if c.payment_due_date else None,
                "trainer_id": c.trainer_id
            }
            for c in clients
        ]
    })


# -------- TRAINERS --------
@gymadmin_bp.get("/trainers")
@jwt_required()
@role_required("gymadmin")
def trainers():
    admin = User.query.get_or_404(get_jwt_identity())

    trainers = User.query.filter_by(
        gym_id=admin.gym_id,
        role="trainer"
    ).all()

    return jsonify({
        "items": [
            {
                "id": t.id,
                "name": t.full_name,
                "email": t.email
            }
            for t in trainers
        ]
    })


# -------- DASHBOARD SUMMARY --------
@gymadmin_bp.get("/dashboard/summary")
@jwt_required()
@role_required("gymadmin")
def dashboard_summary():
    admin = User.query.get(get_jwt_identity())

    return {
        "members": User.query.filter_by(
            gym_id=admin.gym_id,
            role="client"
        ).count(),
        "trainers": User.query.filter_by(
            gym_id=admin.gym_id,
            role="trainer"
        ).count()
    }


# -------- ANNOUNCEMENTS --------
@gymadmin_bp.get("/announcements")
@jwt_required()
@role_required("gymadmin")
def list_announcements():
    admin = User.query.get(get_jwt_identity())

    announcements = Announcement.query.filter_by(
        gym_id=admin.gym_id
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


@gymadmin_bp.post("/announcements")
@jwt_required()
@role_required("gymadmin")
def create_announcement():
    admin = User.query.get(get_jwt_identity())
    data = request.get_json()

    a = Announcement(
        title=data["title"],
        message=data["message"],
        gym_id=admin.gym_id
    )
    db.session.add(a)
    db.session.commit()

    return {"success": True}, 201
