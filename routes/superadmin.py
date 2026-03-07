from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import Gym, User, GymPricing
from routes.decorators import role_required
from utils.mailer import send_gymadmin_invite_email
import secrets
from datetime import datetime, timedelta
import string
from models.audit_log import AuditLog
from models.gym_subscription import GymSubscription
from datetime import datetime, timedelta



superadmin_bp = Blueprint(
    "superadmin",
    __name__,
)

def generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ---------------- GYMS ----------------
@superadmin_bp.get("/gyms")
@jwt_required()
@role_required("superadmin")
def get_gyms():
    gyms = Gym.query.all()
    data = []
    today = datetime.utcnow()

    for gym in gyms:
        members = User.query.filter_by(
            gym_id=gym.id,
            role="client",
            is_active=True
        ).count()

        admin = User.query.filter_by(   
            gym_id=gym.id,
            role="gymadmin"
        ).first()

        sub = (
            GymSubscription.query
            .filter_by(gym_id=gym.id)
            .order_by(GymSubscription.end_date.desc())
            .first()
        )

        plan = None
        end_date = None
        days_left = None
        status = "expired"
        monthly_revenue = members * 300

        if sub:
            plan = sub.plan
            end_date = sub.end_date.isoformat()

            days_left = (sub.end_date - today).days

            if sub.end_date >= today:
                status = "active"

        data.append({
            "id": gym.id,
            "name": gym.name,
            "address": gym.address or "",
            "phone": gym.phone or "",
            "owner_email": admin.email if admin else None,
            "members": members,
            "monthly_revenue_ksh": monthly_revenue,
            "subscription_plan": plan,
            "subscription_end": end_date,
            "days_left": days_left,
            "status": status
        })


    return jsonify(data), 200

@superadmin_bp.get("/gyms/expiring")
@jwt_required()
@role_required("superadmin")
def gyms_expiring():

    today = datetime.utcnow()
    warning_days = 3

    subs = GymSubscription.query.filter_by(is_active=True).all()

    result = []

    for sub in subs:
        days_left = (sub.end_date - today).days
        if days_left < 0:
            continue

        if 0 <= days_left <= warning_days:

            gym = Gym.query.get(sub.gym_id)

            result.append({
                "gym_id": gym.id,
                "gym_name": gym.name,
                "plan": sub.plan,
                "days_left": days_left,
                "end_date": sub.end_date.isoformat()
            })

    return jsonify(result)

@superadmin_bp.post("/gyms/<int:gym_id>/renew")
@jwt_required()
@role_required("superadmin")
def renew_gym(gym_id):

    data = request.get_json() or {}
    plan = data.get("plan")

    if plan == "monthly":
        duration = 30
    elif plan == "yearly":
        duration = 365
    else:
        return {"error": "Invalid Plan"}, 400    

    old_sub = (
        GymSubscription.query
        .filter_by(gym_id=gym_id)
        .order_by(GymSubscription.end_date.desc())
        .first()
    )

    start_date = datetime.utcnow()

    if old_sub and old_sub.end_date > datetime.utcnow():
        start_date = old_sub.end_date

    new_sub = GymSubscription(
        gym_id=gym_id,
        plan=plan,
        start_date=start_date,
        end_date=start_date + timedelta(days=duration),
        is_active=True
    )

    db.session.add(new_sub)
    db.session.commit()

    return {
        "message": "Gym subscription renewed",
        "plan": plan,
        "end_date": new_sub.end_date.isoformat()
    }



@superadmin_bp.post("/gyms")
@jwt_required()
@role_required("superadmin")
def create_gym():
    data = request.get_json() or {}

    name = data.get("name")
    owner_email = data.get("owner_email")

    if not name or not owner_email:
        return {"error": "Gym name and owner email required"}, 400

    if Gym.query.filter_by(name=name).first():
        return {"error": "Gym already exists"}, 409

    if User.query.filter_by(email=owner_email).first():
        return {"error": "Email already in use"}, 409

    # 1️⃣ Create gym
    gym = Gym(
        name=name,
        phone=data.get("phone"),
        address=data.get("address")
    )
    db.session.add(gym)
    db.session.flush()  # get gym.id safely

            # give 14 day trial
    trial = GymSubscription(
        gym_id=gym.id,
        plan="trial",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )

    db.session.add(trial)

    # 2️⃣ Create gymadmin (INACTIVE)
    token = secrets.token_urlsafe(32)

    admin = User(
        email=owner_email,
        role="gymadmin",
        gym_id=gym.id,
        is_active=False,
        password_hash=None,
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.session.add(admin)
    db.session.commit()

    # 3️⃣ Send invite email
    send_gymadmin_invite_email(
        email=admin.email,
        gym_name=gym.name,
        token=token
    )

    return {
        "message": "Gym created. Invite sent to gym admin."
    }, 201




# ---------------- REVENUE ----------------
@superadmin_bp.get("/revenue")
@jwt_required()
@role_required("superadmin")
def platform_revenue():
    gyms = Gym.query.all()

    total = 0
    rows = []

    for gym in gyms:
        members = User.query.filter_by(
            gym_id=gym.id,
            role="client",
            is_active=True
        ).count()

        revenue = members * 300
        total += revenue

        rows.append({
            "gym_id": gym.id,
            "gym_name": gym.name,
            "location": gym.address or "Not provided",
            "members": members,
            "revenue_ksh": revenue
        })

    return jsonify({
        "currency": "KES",
        "total_revenue": total,
        "gyms": rows
    }), 200



# ---------------- USERS ----------------
@superadmin_bp.get("/users")
@jwt_required()
@role_required("superadmin")
def get_all_users():
    users = User.query.all()

    return jsonify([
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "gym_id": u.gym_id,
            "gym_name": u.gym.name if u.gym else None,
            "is_active": u.is_active
        }
        for u in users
    ])



@superadmin_bp.delete("/gyms/<int:gym_id>")
@jwt_required()
@role_required("superadmin")
def delete_gym(gym_id):
    gym = Gym.query.get_or_404(gym_id)
    db.session.delete(gym)
    db.session.commit()
    return jsonify({"message": "Gym deleted"}), 200

# Get all pending gym pricing
@superadmin_bp.get("/pricing/pending")
@jwt_required()
@role_required("superadmin")
def pending_pricing():
    gyms = GymPricing.query.filter_by(approved=False).all()
    return jsonify([
        {
            "id": p.id,
            "gym_id": p.gym_id,
            "gym_name": p.gym.name if p.gym else None,
            "daily_price": float(p.daily_price),
            "monthly_price": float(p.monthly_price)
        }
        for p in gyms
    ]), 200


# Approve a pricing
@superadmin_bp.post("/pricing/<int:pricing_id>/approve")
@jwt_required()
@role_required("superadmin")
def approve_pricing(pricing_id):
    pricing = GymPricing.query.get_or_404(pricing_id)
    pricing.approved = True
    db.session.commit()

    return {"message": f"Pricing for {pricing.gym.name} approved"}, 200


@superadmin_bp.get("/audit-logs")
@jwt_required()
@role_required("superadmin")
def get_audit_logs():

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()

    return jsonify([
        {
            "id": log.id,
            "user": log.user.email if log.user else "System",
            "action": log.action,
            "entity": log.entity,
            "entity_id": log.entity_id,
            "details": log.details,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ])


@superadmin_bp.get("/gyms/<int:gym_id>/subscription")
@jwt_required()
@role_required("superadmin")
def get_gym_subscription(gym_id):

    sub = (
        GymSubscription.query
        .filter_by(gym_id=gym_id)
        .order_by(GymSubscription.end_date.desc())
        .first()
    )

    if not sub:
        return jsonify(None), 200

    today = datetime.utcnow()

    return jsonify({
        "plan": sub.plan,
        "start_date": sub.start_date.isoformat(),
        "end_date": sub.end_date.isoformat(),
        "days_left": (sub.end_date - today).days
    })



