from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt
from routes.decorators import role_required
from extensions import db
from models import Schedule

schedules_bp = Blueprint("schedules", __name__)

@schedules_bp.post("")
@role_required("gymadmin")
def create_schedule():
    data = request.json
    gym_id = get_jwt()["gym_id"]

    sched = Schedule(
        gym_id=gym_id,
        trainer_id=data["trainer_id"],
        client_id=data["client_id"],
        start_time=data["start_time"],
        end_time=data["end_time"]
    )

    db.session.add(sched)
    db.session.commit()

    return jsonify({"message": "Schedule created"}), 201


@schedules_bp.get("")
@role_required("gymadmin")
def list_schedules():
    gym_id = get_jwt()["gym_id"]
    return jsonify([
        {
            "id": s.id,
            "trainer_id": s.trainer_id,
            "client_id": s.client_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "status": s.status
        } for s in Schedule.query.filter_by(gym_id=gym_id).all()
    ])
