from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from routes.decorators import role_required
from models import WorkoutPlan, Payment, Schedule, Subscription, Announcement, User, Message
from datetime import datetime
from extensions import db
client_bp = Blueprint("client", __name__)

# -------- WORKOUT PLANS --------
@client_bp.get("/plans")
@jwt_required()
@role_required("client")
def get_my_plans():
    user_id = int(get_jwt_identity())

    plans = (
        WorkoutPlan.query
        .join(Schedule, Schedule.plan_id == WorkoutPlan.id)
        .filter(
            WorkoutPlan.client_id == user_id,
            Schedule.status != "completed",
        )
        .order_by(Schedule.start_time.desc(), WorkoutPlan.id.desc())
        .all()
    )

    result = []
    seen_plan_ids = set()

    for p in plans:
        if p.id in seen_plan_ids:
            continue
        seen_plan_ids.add(p.id)
        days = []

        for day in p.workout_days:
            exercises = []

            for ex in day.exercises:
                exercises.append({
                    "name": ex.name,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "rest": ex.rest
                })

            days.append({
                "day_name": day.name,
                "exercises": exercises
            })

        result.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "trainer_id": p.trainer_id,
            "trainer_name": p.trainer.full_name if p.trainer else None,
            "days": days
        })

    return jsonify(result)


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
        "plan": sub.plan if sub else None,
        "start_date": sub.start_date if sub else None,
        "end_date": sub.end_date if sub else None
    }


# -------- ANNOUNCEMENTS --------
@client_bp.get("/announcements")
@jwt_required()
@role_required("client")
def client_announcements():
    user = User.query.get(get_jwt_identity())

    announcements = (
        Announcement.query
        .filter(
            Announcement.gym_id == user.gym_id,
            (Announcement.expires_at.is_(None)) |
            (Announcement.expires_at > datetime.utcnow())
        )
        .order_by(Announcement.created_at.desc())
        .all()
    )

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


@client_bp.delete("/chat/message/<int:message_id>")
@jwt_required()
@role_required("client")
def delete_client_message(message_id):
    client_id = int(get_jwt_identity())

    message = Message.query.filter_by(
        id=message_id,
        sender_id=client_id
    ).first()

    if not message:
        return jsonify({"error": "Not allowed"}), 403

    db.session.delete(message)
    db.session.commit()

    return jsonify({"message": "Deleted"}), 200


@client_bp.put("/profile")
@jwt_required()
@role_required("client")
def update_client_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    full_name = data.get("full_name")
    phone = data.get("phone")

    # Split full name into first + last
    if full_name:
        parts = full_name.strip().split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""

    if phone:
        user.phone = phone

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully",
        "user": user.to_dict()
    }), 200


@client_bp.get("/me")
@jwt_required()
@role_required("client")
def get_client_profile():
    user_id = int(get_jwt_identity())

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone
    }), 200

@client_bp.get("/trainer")
@jwt_required()
@role_required("client")
def get_my_trainer():
    client_id = get_jwt_identity()

    client = User.query.get_or_404(client_id)

    if not client.trainer_id:
        return jsonify({"trainer": None})

    trainer = User.query.get(client.trainer_id)

    return jsonify({
        "trainer_id": trainer.id,
        "trainer_name": trainer.full_name,
        "trainer_email": trainer.email
    })
