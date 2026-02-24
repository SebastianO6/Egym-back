from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity
from routes.decorators import role_required
from extensions import db
from models import Schedule, User, WorkoutPlan, WorkoutDay, WorkoutExercise
from datetime import datetime, timedelta

schedules_bp = Blueprint("schedules", __name__)

@schedules_bp.post("")
@jwt_required()
@role_required("trainer", "gymadmin")
def create_schedule():
    data = request.json
    gym_id = get_jwt()["gym_id"]
    trainer_id = int(get_jwt_identity())

    sched = Schedule(
        gym_id=gym_id,
        trainer_id=trainer_id,
        client_id=data["client_id"],
        plan_id=data.get("plan_id"),  # ✅
        start_time=datetime.fromisoformat(data["start_time"]),
        end_time=datetime.fromisoformat(data["end_time"]),
    )

    db.session.add(sched)
    db.session.commit()

    return jsonify({"message": "Schedule created"}), 201



@schedules_bp.get("")
@jwt_required()
@role_required("trainer")
def list_schedules():
    gym_id = get_jwt()["gym_id"]

    q = Schedule.query.filter_by(gym_id=gym_id)

    trainer_id = request.args.get("trainer_id")
    status = request.args.get("status")
    date = request.args.get("date")

    if trainer_id:
        q = q.filter(Schedule.trainer_id == trainer_id)

    if status:
        q = q.filter(Schedule.status == status)

    if date:
        start = datetime.fromisoformat(date)
        end = start + timedelta(days=1)
        q = q.filter(Schedule.start_time >= start, Schedule.start_time < end)

    schedules = q.order_by(Schedule.start_time.asc()).all()

    return jsonify([
        {
            "id": s.id,
            "trainer_id": s.trainer_id,
            "client_id": s.client_id,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "status": s.status
        }
        for s in schedules
    ])


@schedules_bp.get("/client")
@jwt_required()
@role_required("client")
def client_schedule():
    client_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    sessions = Schedule.query.filter_by(
        client_id=client_id,
        gym_id=gym_id
    ).order_by(Schedule.start_time.asc()).all()

    return jsonify([
        {
            "id": s.id,
            "start": s.start_time.isoformat(),
            "end": s.end_time.isoformat(),
            "status": s.status
        }
        for s in sessions
    ])



@schedules_bp.delete("/<int:schedule_id>")
@jwt_required()
@role_required("trainer")
def delete_schedule(schedule_id):
    gym_id = get_jwt()["gym_id"]

    sched = Schedule.query.filter_by(id=schedule_id, gym_id=gym_id).first_or_404()
    db.session.delete(sched)
    db.session.commit()

    return {"message": "Schedule deleted"}, 200


@schedules_bp.get("/trainer")
@jwt_required()
@role_required("trainer")
def trainer_schedule():
    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    sessions = Schedule.query.filter_by(
        trainer_id=trainer_id,
        gym_id=gym_id
    ).order_by(Schedule.start_time.asc()).all()

    results = []

    for s in sessions:
        results.append({
            "id": s.id,
            "client_id": s.client_id,
            "member_name": s.client.full_name if s.client else "Unknown",
            "plan_title": s.plan.title if s.plan else None,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "status": s.status
        })


    return jsonify(results), 200



@schedules_bp.get("/calendar")
@jwt_required()
@role_required("gymadmin")
def calendar_schedules():
    gym_id = get_jwt()["gym_id"]

    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return {"error": "start and end required"}, 400

    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    schedules = Schedule.query.filter(
        Schedule.gym_id == gym_id,
        Schedule.start_time >= start_dt,
        Schedule.start_time <= end_dt
    ).all()

    return jsonify([
        {
            "id": s.id,
            "title": "Training Session",
            "start": s.start_time.isoformat(),
            "end": s.end_time.isoformat(),
            "trainer_id": s.trainer_id,
            "client_id": s.client_id,
            "status": s.status
        }
        for s in schedules
    ])


@schedules_bp.put("/<int:schedule_id>")
@jwt_required()
@role_required("trainer")
def update_schedule(schedule_id):
    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")
    data = request.json

    sched = Schedule.query.filter_by(
        id=schedule_id,
        trainer_id=trainer_id,
        gym_id=gym_id
    ).first_or_404()

    if "status" in data:
        sched.status = data["status"]

    db.session.commit()

    return {"message": "Schedule updated"}, 200


@schedules_bp.get("/trainer/<int:schedule_id>")
@jwt_required()
@role_required("trainer")
def schedule_detail(schedule_id):

    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    sched = Schedule.query.filter_by(
        id=schedule_id,
        trainer_id=trainer_id,
        gym_id=gym_id
    ).first_or_404()

    plan = sched.plan

    days = WorkoutDay.query.filter_by(plan_id=plan.id).all()

    schedule_data = {}

    for day in days:
        exercises = WorkoutExercise.query.filter_by(day_id=day.id).all()

        schedule_data[day.name] = [
            {
                "name": ex.name,
                "sets": ex.sets,
                "reps": ex.reps,
                "rest": ex.rest
            }
            for ex in exercises
        ]

    return jsonify({
        "id": sched.id,
        "client_name": sched.client.full_name,
        "plan_title": plan.title,
        "description": plan.description,
        "schedule": schedule_data,
        "status": sched.status
    })




