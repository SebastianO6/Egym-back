from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from routes.decorators import role_required, block_temp_tokens
from extensions import db
from models import User, WorkoutPlan

trainer_bp = Blueprint("trainer", __name__, url_prefix="/api/trainer")

# ---------------- TRAINER DASHBOARD ----------------

@trainer_bp.get("/members")
@jwt_required()
@role_required("trainer")
@block_temp_tokens
def my_clients():
    claims = get_jwt()
    gym_id = claims.get("gym_id")

    clients = User.query.filter_by(
        role="client",
        gym_id=gym_id,
        is_active=True
    ).all()

    return jsonify([
        {
            "id": c.id,
            "email": c.email,
            "full_name": c.full_name
        } for c in clients
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
@jwt_required()
@role_required("trainer")
@block_temp_tokens
def create_plan():
    data = request.get_json() or {}

    required = ["title", "client_id"]
    if not all(data.get(f) for f in required):
        return {"error": "Missing fields"}, 400

    claims = get_jwt()
    trainer_id = int(get_jwt_identity())
    gym_id = claims.get("gym_id")

    client = User.query.filter_by(
        id=data["client_id"],
        role="client",
        gym_id=gym_id
    ).first()

    if not client:
        return {"error": "Invalid client"}, 404

    plan = WorkoutPlan(
        title=data["title"],
        description=data.get("description"),
        client_id=client.id,
        trainer_id=trainer_id
    )

    db.session.add(plan)
    db.session.commit()

    return {"message": "Workout plan created"}, 201

