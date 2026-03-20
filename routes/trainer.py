from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from routes.decorators import role_required, block_temp_tokens
from extensions import db
from models import User, WorkoutPlan, Payment, ProgressLog, Attendance, Message, Subscription, WorkoutExercise, WorkoutDay, Schedule
from datetime import datetime, timedelta
from utils.audit import log_action


trainer_bp = Blueprint("trainer", __name__, url_prefix="/api/trainer")

# ---------------- TRAINER DASHBOARD ----------------


@trainer_bp.route("/dashboard/summary", methods=["GET"])
@jwt_required()
@role_required("trainer")
def trainer_summary():
    trainer_id = get_jwt_identity()

    total_clients = User.query.filter_by(
        role="client",
        trainer_id=trainer_id,
        is_active=True
    ).count()

    inactive_clients = User.query.filter_by(
        role="client",
        trainer_id=trainer_id,
        is_active=False
    ).count()

    return jsonify({
        "total_clients": total_clients,
        "inactive_clients": inactive_clients
    })


@trainer_bp.get("/members")
@jwt_required()
@role_required("trainer")
@block_temp_tokens
def my_clients():
    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    # ✅ Filter trainer ownership at USER level
    clients = User.query.filter_by(
        role="client",
        gym_id=gym_id,
        trainer_id=trainer_id,
        is_active=True
    ).all()

    results = []

    for c in clients:
        # ✅ Subscription has NO trainer_id
        subscription = Subscription.query.filter_by(
            user_id=c.id,
            gym_id=gym_id,
            is_active=True
        ).first()

        results.append({
            "id": c.id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "full_name": c.full_name,
            "email": c.email,
            "phone": c.phone,
            "age": c.age,
            "goal": c.goal,
            "subscription_end": subscription.end_date.isoformat() if subscription else None
        })

    return jsonify({"items": results}), 200


@trainer_bp.get("/members/<int:member_id>")
@jwt_required()
@role_required("trainer")
@block_temp_tokens
def member_details(member_id):
    trainer_id = int(get_jwt_identity())
    claims = get_jwt()
    gym_id = claims.get("gym_id")

    member = User.query.filter_by(
        id=member_id,
        role="client",
        gym_id=gym_id,
        trainer_id=trainer_id
    ).first_or_404()

    # ✅ Get trainer info safely
    trainer = User.query.get(trainer_id)

    subscription = Subscription.query.filter_by(
        user_id=member.id,
        gym_id=gym_id,
        is_active=True
    ).first()

    return jsonify({
        "id": member.id,
        "full_name": member.full_name,
        "email": member.email,
        "phone": member.phone or "",
        "age": member.age,
        "goal": member.goal,
        "notes": member.trainer_notes,
        "active_plan": subscription.plan if subscription else None,
        "subscription_status": "Active" if subscription else "Inactive",

        # ✅ Added trainer info (nothing else changed)
        "trainer": {
            "id": trainer.id,
            "full_name": trainer.full_name,
            "email": trainer.email,
            "phone": trainer.phone
        }
    })


@trainer_bp.get("/members/<int:member_id>/plans")
@jwt_required()
@role_required("trainer")
@block_temp_tokens
def member_plans(member_id):
    trainer_id = int(get_jwt_identity())

    plans = WorkoutPlan.query.filter_by(
        client_id=member_id,
        trainer_id=trainer_id
    ).all()

    return jsonify({
        "items": [p.to_dict() for p in plans]
    })


@trainer_bp.get("/members/<int:member_id>/progress")
@jwt_required()
@role_required("trainer")
def member_progress(member_id):
    trainer_id = int(get_jwt_identity())

    logs = ProgressLog.query.filter_by(
        client_id=member_id,
        trainer_id=trainer_id
    ).order_by(ProgressLog.created_at.desc()).all()

    return jsonify({
        "items": [l.to_dict() for l in logs]
    })


@trainer_bp.post("/members/<int:member_id>/progress")
@jwt_required()
@role_required("trainer")
def add_progress(member_id):
    trainer_id = int(get_jwt_identity())
    data = request.json

    log = ProgressLog(
        client_id=member_id,
        trainer_id=trainer_id,
        weight=data.get("weight"),
        notes=data.get("notes")
    )

    db.session.add(log)
    log_action(
        "add_progress",
        entity="progress_log",
        entity_id=member_id,
        details={"member_id": member_id, "weight": data.get("weight")},
        session=db.session,
    )
    db.session.commit()

    return {"message": "Progress added"}, 201


@trainer_bp.get("/members/<int:member_id>/payments")
@jwt_required()
@role_required("trainer")
def member_payments(member_id):
    trainer_id = int(get_jwt_identity())

    client = User.query.filter_by(
        id=member_id,
        trainer_id=trainer_id
    ).first_or_404()

    payments = Payment.query.filter_by(
        user_id=client.id
    ).order_by(Payment.created_at.desc()).all()

    return jsonify({
        "items": [p.to_dict() for p in payments]
    })


@trainer_bp.get("/members/<int:member_id>/attendance")
@jwt_required()
@role_required("trainer")
def member_attendance(member_id):
    trainer_id = int(get_jwt_identity())

    records = Attendance.query.filter_by(
        client_id=member_id,
        trainer_id=trainer_id
    ).order_by(Attendance.created_at.desc()).all()

    return jsonify({
        "items": [r.to_dict() for r in records]
    })


# ---------------- WORKOUT PLANS ----------------

@trainer_bp.get("/clients")
@jwt_required()
@role_required("trainer")
def clients():
    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    clients = User.query.filter_by(
        role="client",
        trainer_id=trainer_id,
        gym_id=gym_id,
        is_active=True
    ).all()

    return jsonify({
        "items": [
            {
                "id": c.id,
                "full_name": c.full_name
            }
            for c in clients
        ]
    })


@trainer_bp.get("/workout-plans")
@jwt_required()
@role_required("trainer")
def list_trainer_plans():
    trainer_id = int(get_jwt_identity())
    plans = WorkoutPlan.query.filter_by(trainer_id=trainer_id).all()

    return jsonify({
        "items": [p.to_dict() for p in plans]  # includes client_name
    })


@trainer_bp.post("/workout-plans")
@jwt_required()
@role_required("trainer")
def create_plan():
    data = request.get_json() or {}

    if not data.get("title") or not data.get("client_id"):
        return {"error": "Missing fields"}, 400

    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    # Verify client exists and belongs to this trainer's gym
    client = User.query.filter_by(
        id=data["client_id"],
        role="client",
        gym_id=gym_id
    ).first()

    if not client:
        return {"error": "Invalid client"}, 404

    # Create the workout plan
    plan = WorkoutPlan(
        title=data["title"],
        description=data.get("description"),
        client_id=client.id,
        trainer_id=trainer_id,
        gym_id=gym_id
    )

    db.session.add(plan)
    db.session.flush()  # Get plan.id without committing

    # Create workout days and exercises
    schedule_data = data.get("schedule", {})
    for day_name, exercises in schedule_data.items():
        day = WorkoutDay(
            plan_id=plan.id,
            name=day_name
        )
        db.session.add(day)
        db.session.flush()

        for ex in exercises:
            exercise = WorkoutExercise(
                day_id=day.id,
                name=ex.get("name"),
                sets=ex.get("sets"),
                reps=ex.get("reps"),
                rest=ex.get("rest")
            )
            db.session.add(exercise)

    # 🔥 Assign trainer to client if not already assigned
    if not client.trainer_id:
        client.trainer_id = trainer_id

    # 🔥 AUTO CREATE FIRST SESSION
    first_session = Schedule(
        gym_id=gym_id,
        trainer_id=trainer_id,
        client_id=client.id,
        plan_id=plan.id,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=1),
        status="scheduled"
    )

    db.session.add(first_session)
    log_action(
        "create_workout_plan",
        entity="workout_plan",
        entity_id=plan.id,
        details={"client_id": client.id, "title": plan.title},
        session=db.session,
    )
    db.session.commit()

    return jsonify({
        "message": "Workout plan created successfully",
        "plan_id": plan.id,
        "session_id": first_session.id
    }), 201



@trainer_bp.get("/workout-plans/<int:plan_id>")
@jwt_required()
@role_required("trainer")
def get_plan(plan_id):
    trainer_id = int(get_jwt_identity())
    gym_id = get_jwt().get("gym_id")

    plan = WorkoutPlan.query.filter_by(
        id=plan_id,
        trainer_id=trainer_id,
        gym_id=gym_id
    ).first_or_404()

    days = WorkoutDay.query.filter_by(plan_id=plan.id).all()

    result = {
        "id": plan.id,
        "title": plan.title,
        "description": plan.description,
        "client_id": plan.client_id,
        "days": []
    }

    for day in days:
        exercises = WorkoutExercise.query.filter_by(day_id=day.id).all()

        result["days"].append({
            "day_name": day.name,
            "exercises": [
                {
                    "name": e.name,
                    "sets": e.sets,
                    "reps": e.reps,
                    "rest": e.rest
                }
                for e in exercises
            ]
        })

    return jsonify(result)


@trainer_bp.delete("/workout-plans/<int:plan_id>")
@jwt_required()
@role_required("trainer")
def delete_plan(plan_id):
    trainer_id = int(get_jwt_identity())

    plan = WorkoutPlan.query.filter_by(
        id=plan_id,
        trainer_id=trainer_id
    ).first_or_404()

    Schedule.query.filter_by(plan_id=plan.id).delete(synchronize_session=False)

    WorkoutExercise.query.filter(
        WorkoutExercise.day_id.in_(
            db.session.query(WorkoutDay.id).filter_by(plan_id=plan.id)
        )
    ).delete(synchronize_session=False)

    WorkoutDay.query.filter_by(plan_id=plan.id).delete()
    log_action(
        "delete_workout_plan",
        entity="workout_plan",
        entity_id=plan.id,
        details={"client_id": plan.client_id, "title": plan.title},
        session=db.session,
    )
    db.session.delete(plan)
    db.session.commit()

    return {"message": "Plan deleted"}



@trainer_bp.get("/chat/members")
@jwt_required()
@role_required("trainer")
def get_assigned_clients():
    trainer_id = get_jwt_identity()
    trainer = User.query.get_or_404(trainer_id)

    clients = trainer.clients.filter_by(is_active=True).all()

    results = []

    for client in clients:
        last_message = (
            Message.query.filter(
                ((Message.sender_id == trainer.id) & (Message.receiver_id == client.id)) |
                ((Message.sender_id == client.id) & (Message.receiver_id == trainer.id))
            )
            .order_by(Message.created_at.desc())
            .first()
        )

        results.append({
            "user_id": client.id,
            "name": client.full_name or client.email,
            "last_message": last_message.content if last_message else None,
            "last_message_time": last_message.created_at.isoformat() if last_message else None
        })

    return jsonify(results)

@trainer_bp.get("/chat/<int:client_id>")
@jwt_required()
@role_required("trainer")
def get_conversation(client_id):
    trainer_id = get_jwt_identity()
    trainer = User.query.get_or_404(trainer_id)

    client = User.query.filter_by(
        id=client_id,
        role="client",
        trainer_id=trainer.id,
        gym_id=trainer.gym_id,
        is_active=True
    ).first()

    if not client:
        return jsonify({"error": "Forbidden"}), 403

    messages = Message.query.filter(
        ((Message.sender_id == trainer.id) & (Message.receiver_id == client.id)) |
        ((Message.sender_id == client.id) & (Message.receiver_id == trainer.id))
    ).order_by(Message.created_at.asc()).all()

    return jsonify({
        "items": [m.to_dict(trainer.id) for m in messages]
    })


@trainer_bp.delete("/chat/message/<int:message_id>")
@jwt_required()
@role_required("trainer")
def delete_message(message_id):
    trainer_id = int(get_jwt_identity())

    message = Message.query.filter_by(
        id=message_id,
        sender_id=trainer_id
    ).first()

    if not message:
        return jsonify({"error": "Not allowed"}), 403

    db.session.delete(message)
    db.session.commit()

    return jsonify({"message": "Deleted"}), 200    



@trainer_bp.get("/schedule")
@jwt_required()
@role_required("trainer")
def trainer_schedule():
    trainer_id = int(get_jwt_identity())

    schedules = (
        Schedule.query
        .filter(
            Schedule.trainer_id == trainer_id,
            Schedule.status != "completed"
        )
        .order_by(Schedule.start_time.asc())
        .all()
    )

    return jsonify({
        "items": [s.to_dict() for s in schedules]
    })



@trainer_bp.get("/members/<int:member_id>/overview")
@jwt_required()
@role_required("trainer")
def member_overview(member_id):
    trainer_id = int(get_jwt_identity())

    progress = ProgressLog.query.filter_by(
        client_id=member_id,
        trainer_id=trainer_id
    ).order_by(ProgressLog.created_at.desc()).first()

    attendance = Attendance.query.filter_by(
        client_id=member_id,
        trainer_id=trainer_id
    ).order_by(Attendance.created_at.desc()).first()

    plan = WorkoutPlan.query.filter_by(
        client_id=member_id,
        trainer_id=trainer_id
    ).first()

    return jsonify({
        "last_progress": progress.to_dict() if progress else None,
        "last_attendance": attendance.to_dict() if attendance else None,
        "active_plan": plan.to_dict() if plan else None
    })


@trainer_bp.get("/profile")
@jwt_required()
@role_required("trainer")
def get_trainer_profile():
    trainer_id = get_jwt_identity()
    trainer = User.query.get_or_404(trainer_id)
    return jsonify({
        "id": trainer.id,
        "full_name": trainer.full_name,
        "email": trainer.email,
        "phone": trainer.phone
    })


@trainer_bp.put("/profile")
@jwt_required()
@role_required("trainer")
def update_trainer_profile():
    trainer_id = get_jwt_identity()
    data = request.json
    trainer = User.query.get_or_404(trainer_id)

    trainer.first_name = data.get("first_name", trainer.first_name)
    trainer.last_name = data.get("last_name", trainer.last_name)
    trainer.email = data.get("email", trainer.email)
    trainer.phone = data.get("phone", trainer.phone)

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200


@trainer_bp.put("/change-password")
@jwt_required()
@role_required("trainer")
def change_trainer_password():
    trainer_id = get_jwt_identity()
    data = request.json
    trainer = User.query.get_or_404(trainer_id)

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not trainer.check_password(current_password):
        return jsonify({"error": "Incorrect current password"}), 400

    trainer.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200


