from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from decorators import role_required
from extensions import db
from models import Client, WorkoutPlan

trainer_bp = Blueprint("trainer", __name__)

# ---------------- ASSIGNED CLIENTS ----------------

@trainer_bp.get("/trainer/clients")
@role_required("trainer")
def trainer_clients():
    trainer_id = int(get_jwt_identity())

    clients = Client.query.filter_by(trainer_id=trainer_id).all()

    return jsonify([
        {
            "client_id": c.id,
            "subscription_active": c.subscription_active
        }
        for c in clients
    ])

# ---------------- CREATE WORKOUT PLAN ----------------

@trainer_bp.post("/trainer/workouts")
@role_required("trainer")
def create_workout():
    trainer_id = int(get_jwt_identity())
    data = request.json

    client = Client.query.filter_by(
        id=data["client_id"],
        trainer_id=trainer_id
    ).first_or_404()

    plan = WorkoutPlan(
        trainer_id=trainer_id,
        client_id=client.id,
        title=data["title"],
        description=data["description"]
    )

    db.session.add(plan)
    db.session.commit()

    return jsonify({"message": "Workout plan created"}), 201
