from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from routes.decorators import role_required
from extensions import db
from models import User, WorkoutPlan

trainer_bp = Blueprint("trainer", __name__, url_prefix="/api/trainer")

# ---------------- TRAINER DASHBOARD ----------------

@trainer_bp.get("/members")
@role_required("trainer")
def my_clients():
    trainer_id = get_jwt_identity()

    clients = User.query.filter_by(
        role="client",
        is_active=True
    ).all()

    return jsonify([
        {
            "id": c.id,
            "email": c.email,
            "full_name": c.full_name
        }
        for c in clients
    ])

# ---------------- WORKOUT PLANS ----------------

@trainer_bp.get("/clients")
@role_required("trainer")
def clients():
    clients = User.query.filter_by(role="client").all()

    return jsonify({
        "items": [
            {
                "id": c.id,
                "full_name": c.full_name
            } for c in clients
        ]
    })

@trainer_bp.post("/workout-plans")
@role_required("trainer")
def create_plan():
    data = request.json

    plan = WorkoutPlan(
        title=data["title"],
        description=data.get("description"),
        client_id=data["client_id"],
        trainer_id=get_jwt_identity()
    )

    db.session.add(plan)
    db.session.commit()

    return jsonify({"message": "Workout plan created"}), 201
