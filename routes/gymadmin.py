from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import func
from datetime import datetime, timedelta
import secrets
from flask import g

from extensions import db
from models import User, Announcement
from models.subscription import Subscription
from models.payment import Payment

from routes.decorators import role_required, gym_required
from utils.auth import current_admin
from utils.mailer import send_gymadmin_invite_email
from models.gym_pricing import GymPricing
from models.schedule import Schedule

gymadmin_bp = Blueprint("gymadmin", __name__)

# =====================================================
# MEMBERS
# =====================================================
@gymadmin_bp.get("/dashboard")
@role_required("gymadmin")
@gym_required
@jwt_required()
def dashboard():

    admin = current_admin()

    members_count = User.query.filter_by(
        gym_id=admin.gym_id,
        role="client"
    ).count()

    trainers_count = User.query.filter_by(
        gym_id=admin.gym_id,
        role="trainer"
    ).count()

    today = datetime.utcnow().date()

    today_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.gym_id == admin.gym_id,
            func.date(Payment.created_at) == today
        )
        .scalar()
    )

    month_start = today.replace(day=1)

    month_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.gym_id == admin.gym_id,
            Payment.created_at >= month_start
        )
        .scalar()
    )

    trainer_workload = (
        db.session.query(
            User.id,
            User.email,
            func.count(Subscription.id)
        )
        .join(Subscription, Subscription.user_id == User.id, isouter=True)
        .filter(
            User.gym_id == admin.gym_id,
            User.role == "trainer"
        )
        .group_by(User.id)
        .all()
    )

    return jsonify({
        "members": members_count,
        "trainers": trainers_count,
        "revenue": {
            "today": today_revenue,
            "this_month": month_revenue
        },
        "trainer_workload": [
            {
                "trainer_id": t[0],
                "name": t[1],
                "members": t[2]
            }
            for t in trainer_workload
        ]
    }), 200

@gymadmin_bp.get("/members")
@role_required("gymadmin")
@gym_required
@jwt_required()

def list_members():
    admin = current_admin()

    members = User.query.filter_by(
        gym_id=admin.gym_id,
        role="client"
    ).all()

    return jsonify({"items": [m.to_dict() for m in members]}), 200


@gymadmin_bp.get("/members/<int:id>")
@role_required("gymadmin")
@gym_required
@jwt_required()

def get_member(id):
    admin = current_admin()

    member = User.query.filter_by(
        id=id,
        gym_id=admin.gym_id,
        role="client"
    ).first_or_404()

    sub = Subscription.query.filter_by(
        user_id=member.id,
        gym_id=admin.gym_id,
        is_active=True
    ).first()

    data = member.to_dict()
    data["subscription"] = sub.to_dict() if sub else None

    return jsonify(data), 200


@gymadmin_bp.put("/members/<int:id>")
@role_required("gymadmin")
@gym_required
@jwt_required()

def update_member(id):
    admin = current_admin()
    data = request.get_json() or {}

    member = User.query.filter_by(
        id=id,
        gym_id=admin.gym_id,
        role="client"
    ).first_or_404()

    # Trainer change
    if "trainer_id" in data:
        trainer = User.query.filter_by(
            id=data["trainer_id"],
            gym_id=admin.gym_id,
            role="trainer"
        ).first_or_404()
        member.trainer_id = trainer.id

    db.session.commit()
    return jsonify(member.to_dict()), 200


@gymadmin_bp.delete("/members/<int:id>")
@role_required("gymadmin")
@gym_required
@jwt_required()
def delete_member(id):
    admin = current_admin()

    member = User.query.filter_by(
        id=id,
        gym_id=admin.gym_id,
        role="client"
    ).first_or_404()

    # 🔥 DELETE DEPENDENCIES FIRST
    Subscription.query.filter_by(
        user_id=member.id,
        gym_id=admin.gym_id
    ).delete()

    Payment.query.filter_by(
        user_id=member.id,
        gym_id=admin.gym_id
    ).delete()

    db.session.delete(member)
    db.session.commit()

    return jsonify({"message": "Member deleted"}), 200



@gymadmin_bp.post("/members/invite")
@role_required("gymadmin")
@gym_required
@jwt_required()

def invite_member():
    admin = current_admin()
    data = request.get_json() or {}
    email = data.get("email")

    if not email:
        return {"error": "Email required"}, 400

    existing = User.query.filter_by(email=email).first()

    if existing and existing.is_active:
        return {"error": "Member already exists"}, 409

    if existing and not existing.is_active:
        db.session.delete(existing)
        db.session.commit()

    token = secrets.token_urlsafe(32)

    member = User(
        email=email,
        role="client",
        gym_id=admin.gym_id,
        is_active=False,
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24),
        must_change_password=True
    )

    db.session.add(member)
    db.session.commit()

    send_gymadmin_invite_email(email, admin.gym.name, token, role="client")

    return jsonify({"message": "Invite sent"}), 201


# =====================================================
# TRAINERS
# =====================================================

@gymadmin_bp.get("/trainers")
@role_required("gymadmin")
@gym_required
@jwt_required()

def list_trainers():
    admin = current_admin()

    trainers = User.query.filter_by(
        gym_id=admin.gym_id,
        role="trainer"
    ).all()

    return jsonify({
        "items": [t.to_dict() for t in trainers]
    }), 200

@gymadmin_bp.get("/trainers/<int:trainer_id>")
@jwt_required()
@role_required("gymadmin")
def get_trainer(trainer_id):
    admin = current_admin()

    trainer = User.query.filter_by(
        id=trainer_id,
        gym_id=admin.gym_id,
        role="trainer"
    ).first_or_404()

    return jsonify(trainer.to_dict()), 200

@gymadmin_bp.put("/trainers/<int:id>")
@role_required("gymadmin")
@gym_required
@jwt_required()

def update_trainer(id):
    admin = current_admin()
    data = request.get_json() or {}

    trainer = User.query.filter_by(
        id=id,
        gym_id=admin.gym_id,
        role="trainer"
    ).first_or_404()

    trainer.bio = data.get("bio", trainer.bio)
    db.session.commit()

    return jsonify(trainer.to_dict()), 200


@gymadmin_bp.delete("/trainers/<int:id>")
@jwt_required()
@role_required("gymadmin")
def delete_trainer(id):
    admin = current_admin()

    trainer = User.query.filter_by(
        id=id,
        gym_id=admin.gym_id,
        role="trainer"
    ).first_or_404()

    db.session.delete(trainer)
    db.session.commit()

    return jsonify({"message": "Trainer deleted"}), 200


@gymadmin_bp.post("/trainers/invite")
@role_required("gymadmin")
@gym_required
@jwt_required()

def invite_trainer():
    admin = current_admin()
    data = request.get_json() or {}

    # 🔐 Extract fields safely
    email = data.get("email")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    phone = data.get("phone")

    if not email or not isinstance(email, str):
        return jsonify({"error": "Valid email is required"}), 400

    # 🔍 Check existing user
    existing = User.query.filter_by(email=email).first()

    if existing:
        if existing.is_active:
            return jsonify({"error": "Trainer already exists"}), 409

        # Inactive / expired invite → replace
        db.session.delete(existing)
        db.session.commit()


    # 🔑 Create invite
    token = secrets.token_urlsafe(32)

    trainer = User(
        email=email,
        role="trainer",
        gym_id=admin.gym_id,
        is_active=False,
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24),
        must_change_password=True
    )

    db.session.add(trainer)
    db.session.commit()

    # 📧 Send invite AFTER commit
    send_gymadmin_invite_email(
        email=email,
        gym_name=admin.gym.name,
        token=token,
        role="trainer"
    )

    return jsonify({"message": "Trainer invite sent"}), 201
    






# =====================================================
# SUBSCRIPTIONS / PLANS
# =====================================================

@gymadmin_bp.post("/members/<int:member_id>/renew")
@jwt_required()
@role_required("gymadmin")
@gym_required
def renew_member(member_id):
    admin = current_admin()
    data = request.get_json() or {}

    plan = data.get("plan")
    if plan not in ("daily", "monthly"):
        return {"error": "Plan must be 'daily' or 'monthly'"}, 400

    pricing = GymPricing.query.filter_by(
        gym_id=admin.gym_id,
        approved=True
    ).first()

    if not pricing:
        return {"error": "Pricing not approved yet"}, 400

    plan = plan.lower()

    amount = (
        pricing.daily_price
        if plan == "daily"
        else pricing.monthly_price
    )

    # Expire old subscriptions
    Subscription.query.filter_by(
        user_id=member_id,
        gym_id=admin.gym_id,
        is_active=True
    ).update({"is_active": False})

    end_date = datetime.utcnow() + (
        timedelta(days=1) if plan == "daily" else timedelta(days=30)
    )

    sub = Subscription(
        user_id=member_id,
        gym_id=admin.gym_id,
        plan=plan,
        end_date=end_date,
        is_active=True
    )

    payment = Payment(
        user_id=member_id,
        gym_id=admin.gym_id,
        amount=amount,
        method="cash",
        status="paid"
    )

    db.session.add_all([sub, payment])
    db.session.commit()

    return {"message": "Subscription renewed & payment recorded"}, 201


@gymadmin_bp.post("/members/<int:member_id>/assign-trainer")
@jwt_required()
@role_required("gymadmin")
@gym_required
def assign_trainer(member_id):
    admin = current_admin()
    data = request.get_json()
    trainer_id = data.get("trainer_id")

    if not trainer_id:
        return jsonify({"error": "trainer_id required"}), 400

    member = User.query.filter_by(
        id=member_id,
        role="client",
        gym_id=admin.gym_id
    ).first_or_404()

    trainer = User.query.filter_by(
        id=trainer_id,
        role="trainer",
        gym_id=admin.gym_id,
        is_active=True
    ).first_or_404()

    member.trainer_id = trainer.id

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Assignment failed"}), 500

    return jsonify({
        "message": "Trainer assigned successfully",
        "member_id": member.id,
        "trainer_id": trainer.id
    }), 200



@gymadmin_bp.get("/announcements")
@role_required("gymadmin")
@gym_required
@jwt_required()
def list_announcements():
    admin = current_admin()

    anns = Announcement.query.filter_by(
        gym_id=admin.gym_id
    ).order_by(Announcement.created_at.desc()).all()

    return jsonify([a.to_dict() for a in anns]), 200



@gymadmin_bp.post("/announcements")
@jwt_required()
@role_required("gymadmin")
@gym_required
def create_announcement():
    admin = current_admin()
    data = request.get_json() or {}

    announcement = Announcement(
        title=data["title"],
        message=data["message"],
        tag=data.get("tag", "general"),
        gym_id=admin.gym_id,          
        author_id=admin.id
    )

    db.session.add(announcement)
    db.session.commit()

    return jsonify(announcement.to_dict()), 201





@gymadmin_bp.put("/announcements/<int:id>")
@role_required("gymadmin")
@gym_required
@jwt_required()

def update_announcement(id):
    admin = current_admin()
    data = request.get_json() or {}

    ann = Announcement.query.filter_by(
        id=id,
        gym_id=admin.gym_id
    ).first_or_404()

    ann.title = data["title"]
    ann.message = data["message"]
    ann.tag = data.get("tag", ann.tag)

    db.session.commit()
    return jsonify(ann.to_dict()), 200


@gymadmin_bp.delete("/announcements/<int:id>")
@role_required("gymadmin")
@gym_required
@jwt_required()

def delete_announcement(id):
    admin = current_admin()

    ann = Announcement.query.filter_by(
        id=id,
        gym_id=admin.gym_id
    ).first_or_404()

    db.session.delete(ann)
    db.session.commit()

    return jsonify({"message": "Deleted"}), 200


@gymadmin_bp.get("/revenue")
@role_required("gymadmin")
@gym_required
@jwt_required()

def revenue_summary():
    gym_id = get_jwt()["gym_id"]

    pricing = GymPricing.query.filter_by(gym_id=gym_id, approved=True).first()
    daily_price = float(pricing.daily_price) if pricing else 300
    monthly_price = float(pricing.monthly_price) if pricing else 300

    # Active subscriptions
    active_subs = Subscription.query.filter_by(
        gym_id=gym_id,
        is_active=True
    ).all()

    total_revenue = 0
    for sub in active_subs:
        if sub.plan.lower() == "daily":
            total_revenue += daily_price
        else:
            total_revenue += monthly_price

    active_members = len(active_subs)

    return jsonify({
        "total_revenue": float(total_revenue),
        "active_members": active_members,
        "daily_price": daily_price,
        "monthly_price": monthly_price
    }), 200

@gymadmin_bp.get("/revenue/series")
@jwt_required()
@role_required("gymadmin")
@gym_required
def revenue_series():
    admin = current_admin()

    rows = (
        db.session.query(
            func.date(Payment.created_at).label("date"),
            func.coalesce(func.sum(Payment.amount), 0).label("amount")
        )
        .filter(Payment.gym_id == admin.gym_id)
        .group_by(func.date(Payment.created_at))
        .order_by(func.date(Payment.created_at))
        .all()
    )

    return jsonify([
        {
            "date": r.date.isoformat(),
            "amount": float(r.amount)
        }
        for r in rows
    ]), 200


@gymadmin_bp.get("/pricing")
@jwt_required()
@role_required("gymadmin")
@gym_required
def get_pricing():
    admin = current_admin()

    pricing = GymPricing.query.filter_by(
        gym_id=admin.gym_id
    ).first()

    if not pricing:
        return jsonify(None), 200

    return jsonify({
        "daily_price": pricing.daily_price,
        "monthly_price": pricing.monthly_price,
        "approved": pricing.approved
    }), 200


@gymadmin_bp.post("/pricing")
@jwt_required()
@role_required("gymadmin")
@gym_required
def set_pricing():
    admin = current_admin()
    data = request.get_json() or {}
    daily = data.get("daily_price")
    monthly = data.get("monthly_price")

    if daily is None or monthly is None:
        return {"error": "Daily and monthly price required"}, 400

    pricing = GymPricing.query.filter_by(gym_id=admin.gym_id).first()
    if not pricing:
        pricing = GymPricing(gym_id=admin.gym_id)

    pricing.daily_price = daily
    pricing.monthly_price = monthly
    pricing.approved = False  # Reset approval on change

    db.session.add(pricing)
    db.session.commit()

    return {"message": "Pricing submitted for approval"}, 201


@gymadmin_bp.get("/members/<int:member_id>/payments")
@role_required("gymadmin")
@gym_required
@jwt_required()

def member_payments(member_id):
    admin = current_admin()

    payments = Payment.query.filter_by(
        user_id=member_id,
        gym_id=admin.gym_id
    ).order_by(Payment.created_at.desc()).all()

    return jsonify([
        {
            "id": p.id,
            "amount": float(p.amount),
            "method": p.method,
            "status": p.status,
            "created_at": p.created_at.isoformat()
        }
        for p in payments
    ])

@gymadmin_bp.post("/invites/<int:id>/resend")
@role_required("gymadmin")
@gym_required
@jwt_required()

def resend_invite(id):
    admin = current_admin()

    user = User.query.filter_by(
        id=id,
        gym_id=admin.gym_id,
        is_active=False
    ).first_or_404()

    token = secrets.token_urlsafe(32)
    user.invite_token = token
    user.invite_expires_at = datetime.utcnow() + timedelta(hours=24)

    db.session.commit()

    send_gymadmin_invite_email(
        email=user.email,
        gym_name=admin.gym.name,
        token=token,
        role=user.role
    )

    return {"success": True}


@gymadmin_bp.get("/schedules")
@role_required("gymadmin")
@gym_required
@jwt_required()

def list_schedules():
    admin = current_admin()

    schedules = Schedule.query.filter_by(
        gym_id=admin.gym_id
    ).order_by(Schedule.start_time.asc()).all()

    return jsonify([
        {
            "id": s.id,
            "trainer_id": s.trainer_id,
            "member_id": s.member_id,
            "title": s.title,
            "start": s.start_time.isoformat(),
            "end": s.end_time.isoformat()
        }
        for s in schedules
    ])


    
@gymadmin_bp.get("/profile")
@jwt_required()
@role_required("gymadmin")
@gym_required
def get_profile():
    admin = current_admin()

    return jsonify({
        "user": {
            "id": admin.id,
            "email": admin.email,
            "name": f"{admin.first_name or ''} {admin.last_name or ''}".strip()
        },
        "gym": {
            "name": admin.gym.name,
            "address": admin.gym.address,
            "phone": admin.gym.phone,
            "status": admin.gym.status
        }
    }), 200


@gymadmin_bp.put("/profile")
@jwt_required()
@role_required("gymadmin")
def update_profile():
    admin = current_admin()
    data = request.get_json() or {}

    admin.email = data.get("email", admin.email)
    db.session.commit()

    return jsonify({"message": "Profile updated"}), 200
