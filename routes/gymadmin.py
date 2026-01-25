from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import User, Announcement
from routes.decorators import role_required, gym_required
from utils.auth import get_current_user
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from utils.auth import current_admin
from utils.auth import invite_user
from models.subscription import Subscription
from utils.subscriptions import PLAN_DURATIONS
from models.payment import Payment
from sqlalchemy import func



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
                "email": c.email,
                "is_active": c.is_active,
                "trainer_id": getattr(c, "trainer_id", None),
                "created_at": c.created_at.isoformat()
            }
            for c in clients
        ]
    })



@gymadmin_bp.post("/members")
@jwt_required()
@role_required("gymadmin")
def invite_member():
    admin = User.query.get_or_404(get_jwt_identity())
    data = request.get_json()

    email = data.get("email")
    if not email:
        return {"error": "Email is required"}, 400

    if User.query.filter_by(email=email).first():
        return {"error": "Email already exists"}, 409

    token = secrets.token_urlsafe(32)

    user = User(
        email=email,
        role="client",
        gym_id=admin.gym_id,
        is_active=True,
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Invite created",
        "invite_link": f"https://yourapp.com/accept-invite?token={token}"
    }), 201





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

@gymadmin_bp.post("/trainers")
def create_trainer():
    admin = current_admin()
    data = request.get_json()

    email = data.get("email")
    bio = data.get("bio", "")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    token = invite_user(
        email=email,
        role="trainer",
        gym_id=admin.gym_id
    )

    invite_link = f"https://yourapp.com/accept-invite?token={token}"

    # TODO: send email here
    # send_email(email, invite_link)

    return jsonify({
        "message": "Trainer invited successfully",
        "invite_link": invite_link  # optional for dev
    }), 201



# -------- DASHBOARD SUMMARY --------
@gymadmin_bp.get("/dashboard/summary")
@jwt_required()
@role_required("gymadmin")
def dashboard_summary():
    admin = current_admin()

    members_count = User.query.filter_by(
        gym_id=admin.gym_id,
        role="client"
    ).count()

    trainers = User.query.filter_by(
        gym_id=admin.gym_id,
        role="trainer"
    ).all()

    workload = [
        {
            "trainer_id": t.id,
            "member_count": User.query.filter_by(
                trainer_id=t.id
            ).count()
        }
        for t in trainers
    ]

    return {
        "members": {"total": members_count},
        "trainers": {
            "total": len(trainers),
            "workload": workload
        }
    }


# -------- ANNOUNCEMENTS --------
@gymadmin_bp.get("/announcements")
@jwt_required()
@role_required("gymadmin")
def list_announcements():
    admin = current_admin()

    anns = Announcement.query.filter_by(
        gym_id=admin.gym_id
    ).order_by(Announcement.created_at.desc()).all()

    return jsonify([{
        "id": a.id,
        "title": a.title,
        "message": a.message,
        "tag": a.tag,
        "gym_id": a.gym_id,
        "created_at": a.created_at.isoformat()
    } for a in anns])



@gymadmin_bp.post("/announcements")
@jwt_required()
@role_required("gymadmin")
def create_announcement():
    admin = current_admin()
    data = request.get_json()

    ann = Announcement(
        title=data["title"],
        message=data["message"],
        tag=data.get("tag", "general"),
        gym_id=admin.gym_id,
        author_id=admin.id
    )

    db.session.add(ann)
    db.session.commit()

    return {"message": "Announcement created"}, 201

@gymadmin_bp.put("/announcements/<int:id>")
@jwt_required()
@role_required("gymadmin")
def update_announcement(id):
    admin = current_admin()

    ann = Announcement.query.filter_by(
        id=id,
        gym_id=admin.gym_id
    ).first_or_404()

    data = request.get_json()
    ann.title = data["title"]
    ann.message = data["message"]
    ann.tag = data.get("tag", ann.tag)

    db.session.commit()
    return {"message": "Updated"}

@gymadmin_bp.delete("/announcements/<int:id>")
@jwt_required()
@role_required("gymadmin")
def delete_announcement(id):
    admin = current_admin()

    ann = Announcement.query.filter_by(
        id=id,
        gym_id=admin.gym_id
    ).first_or_404()

    db.session.delete(ann)
    db.session.commit()
    return {"message": "Deleted"}




@gymadmin_bp.post("/members/<int:member_id>/assign-trainer")
@jwt_required()
@role_required("gymadmin")
def assign_trainer(member_id):
    admin = current_admin()
    data = request.get_json()

    trainer_id = data.get("trainer_id")

    member = User.query.filter_by(
        id=member_id,
        gym_id=admin.gym_id,
        role="client"
    ).first_or_404()

    active_sub = Subscription.query.filter_by(
        user_id=member.id,
        gym_id=admin.gym_id,
        is_active=True
    ).first()

    if not active_sub:
        return jsonify({"error": "Client has no active subscription"}), 400

    trainer = User.query.filter_by(
        id=trainer_id,
        gym_id=admin.gym_id,
        role="trainer"
    ).first_or_404()

    member.trainer_id = trainer.id
    db.session.commit()

    return jsonify({"message": "Trainer assigned"}), 200


@gymadmin_bp.post("/members/<int:member_id>/renew")
@jwt_required()
@role_required("gymadmin")
@gym_required
def renew_member(member_id):
    data = request.get_json()
    plan = data.get("plan")

    if not plan:
        return {"error": "Plan is required"}, 400

    days = PLAN_DURATIONS.get(plan)
    if not days:
        return {"error": "Invalid plan"}, 400

    gym_id = get_jwt()["gym_id"]

    # deactivate old subscriptions
    Subscription.query.filter_by(
        user_id=member_id,
        gym_id=gym_id,
        is_active=True
    ).update({"is_active": False})

    sub = Subscription(
        user_id=member_id,
        gym_id=gym_id,
        plan=plan,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=days),
        is_active=True
    )

    db.session.add(sub)
    db.session.commit()

    return {"message": "Subscription renewed successfully"}, 201





@gymadmin_bp.get("/revenue")
@jwt_required()
@role_required("gymadmin")
@gym_required
def revenue_summary():
    gym_id = get_jwt()["gym_id"]

    active_members = Subscription.query.filter_by(
        gym_id=gym_id,
        is_active=True
    ).count()

    total_revenue = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(Payment.gym_id == gym_id).scalar()

    return jsonify({
        "total_revenue": float(total_revenue),
        "active_members": active_members,
        "premium_members": 0
    })

@gymadmin_bp.get("/membership/expiring")
@jwt_required()
@role_required("gymadmin")
@gym_required
def expiring_members():
    gym_id = get_jwt()["gym_id"]

    upcoming = Subscription.query.filter(
        Subscription.gym_id == gym_id,
        Subscription.is_active == True,
        Subscription.end_date <= datetime.utcnow() + timedelta(days=7)
    ).all()

    return jsonify([
        {
            "member_id": s.user_id,
            "due_date": s.end_date.date().isoformat()
        }
        for s in upcoming
    ])






