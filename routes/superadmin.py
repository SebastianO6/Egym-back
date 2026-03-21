from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from extensions import db
from models import (
    Announcement,
    Attendance,
    AuditLog,
    Gym,
    GymPricing,
    GymSubscription,
    Message,
    Payment,
    ProgressLog,
    Schedule,
    Subscription,
    User,
    WorkoutDay,
    WorkoutExercise,
    WorkoutPlan,
)
from routes.decorators import role_required
from utils.mailer import send_gymadmin_invite_email
from utils.audit import log_action
from utils.pricing import calculate_gym_pricing, get_active_member_count
import secrets
from datetime import datetime, timedelta
import string
import re
from sqlalchemy import delete, func, or_, select, update

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
        members = get_active_member_count(gym.id)

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
        subscription_status = "expired"

        if sub:
            plan = sub.plan
            end_date = sub.end_date.isoformat()
            days_left = (sub.end_date - today).days

            if sub.end_date >= today:
                subscription_status = "active"

        pricing_breakdown = calculate_gym_pricing(members)

        data.append({
            "id": gym.id,
            "name": gym.name,
            "slug": gym.slug,
            "join_url": build_join_url(gym.slug) if gym.slug else None,
            "address": gym.address or "",
            "phone": gym.phone or "",
            "owner_email": admin.email if admin else None,
            "members": members,
            "monthly_revenue_ksh": pricing_breakdown["final_price"],
            "pricing_breakdown": pricing_breakdown,

            # subscription info
            "subscription_plan": plan,
            "subscription_end": end_date,
            "days_left": days_left,
            "subscription_status": subscription_status,

            # real gym status
            "status": gym.status
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
    log_action(
        "renew_gym_subscription",
        entity="gym_subscription",
        entity_id=gym_id,
        details={"gym_id": gym_id, "plan": plan},
        session=db.session,
    )
    db.session.commit()

    return {
        "message": "Gym subscription renewed",
        "plan": plan,
        "end_date": new_sub.end_date.isoformat()
    }




# -----------------------------
# 🔥 SLUG GENERATOR
# -----------------------------
def generate_unique_slug(name):
    base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = base_slug
    count = 1

    while Gym.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{count}"
        count += 1

    return slug


def build_join_url(slug):
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{frontend_url}/join/{slug}"


# -----------------------------
# ✅ CREATE GYM
# -----------------------------
@superadmin_bp.post("/gyms")
@jwt_required()
@role_required("superadmin")
def create_gym():
    data = request.get_json() or {}

    name = data.get("name")
    owner_email = data.get("owner_email")

    if not name or not owner_email:
        return {"error": "Gym name and owner email required"}, 400

    # Prevent duplicates
    if Gym.query.filter_by(name=name).first():
        return {"error": "Gym already exists"}, 409

    if User.query.filter_by(email=owner_email).first():
        return {"error": "Email already in use"}, 409

    # 🔥 Generate slug automatically
    slug = generate_unique_slug(name)

    # 1️⃣ Create gym
    gym = Gym(
        name=name,
        slug=slug,
        phone=data.get("phone"),
        address=data.get("address"),
        status="pending"
    )
    db.session.add(gym)
    db.session.flush()  # ensures gym.id is available

    # 2️⃣ Create trial subscription
    trial = GymSubscription(
        gym_id=gym.id,
        plan="trial",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    db.session.add(trial)

    # 3️⃣ Create gym admin (inactive + invite)
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

    log_action(
        "create_gym",
        entity="gym",
        entity_id=gym.id,
        details={"name": gym.name, "slug": gym.slug, "admin_email": owner_email},
        session=db.session,
    )
    db.session.commit()

    # 4️⃣ Send invite email
    email_sent = True
    warning = None

    try:
        send_gymadmin_invite_email(
            email=admin.email,
            gym_name=gym.name,
            token=token
        )
    except Exception:
        email_sent = False
        warning = "Gym was created, but the invite email could not be sent."
        current_app.logger.exception("Failed to send gym admin invite for gym %s", gym.id)

    return jsonify({
        "message": "Gym created. Invite sent to gym admin." if email_sent else "Gym created, but invite email was not sent.",
        "gym": {
            "id": gym.id,
            "name": gym.name,
            "slug": gym.slug,
            "join_url": build_join_url(gym.slug),
            "status": gym.status
        },
        "admin_email": admin.email,
        "email_sent": email_sent,
        "warning": warning
    }), 201


# -----------------------------
# ✅ UPDATE GYM
# -----------------------------
@superadmin_bp.put("/gyms/<int:gym_id>")
@jwt_required()
@role_required("superadmin")
def update_gym(gym_id):

    gym = Gym.query.get_or_404(gym_id)
    data = request.get_json() or {}

    # 🔥 Handle name + slug update
    new_name = data.get("name")

    if new_name and new_name != gym.name:
        gym.name = new_name
        gym.slug = generate_unique_slug(new_name)

    # Other updates (unchanged)
    gym.phone = data.get("phone", gym.phone)
    gym.address = data.get("address", gym.address)
    gym.status = data.get("status", gym.status)

    log_action(
        "update_gym",
        entity="gym",
        entity_id=gym.id,
        details={"name": gym.name, "slug": gym.slug, "status": gym.status},
        session=db.session,
    )
    db.session.commit()

    return jsonify({
        "id": gym.id,
        "name": gym.name,
        "slug": gym.slug,
        "join_url": build_join_url(gym.slug) if gym.slug else None,
        "phone": gym.phone,
        "address": gym.address,
        "status": gym.status
    }), 200




# ---------------- REVENUE ----------------
@superadmin_bp.get("/revenue")
@jwt_required()
@role_required("superadmin")
def platform_revenue():
    gyms = Gym.query.all()

    total = 0
    rows = []

    for gym in gyms:
        members = get_active_member_count(gym.id)
        pricing_breakdown = calculate_gym_pricing(members)
        total += pricing_breakdown["final_price"]

        rows.append({
            "gym_id": gym.id,
            "gym_name": gym.name,
            "location": gym.address or "Not provided",
            "members": members,
            "revenue_ksh": pricing_breakdown["final_price"],
            "pricing_breakdown": pricing_breakdown,
        })

    return jsonify({
        "currency": "KES",
        "total_revenue": total,
        "gyms": rows
    }), 200


@superadmin_bp.get("/billing/member-growth")
@jwt_required()
@role_required("superadmin")
def member_growth_report():
    rows = (
        db.session.query(
            Gym.id.label("gym_id"),
            Gym.name.label("gym_name"),
            func.date_trunc("month", User.created_at).label("month"),
            func.count(User.id).label("new_members"),
        )
        .join(User, User.gym_id == Gym.id)
        .filter(User.role == "client")
        .group_by(Gym.id, Gym.name, func.date_trunc("month", User.created_at))
        .order_by(func.date_trunc("month", User.created_at).desc(), Gym.name.asc())
        .all()
    )

    return jsonify([
        {
            "gym_id": row.gym_id,
            "gym_name": row.gym_name,
            "month": row.month.date().isoformat(),
            "new_members": row.new_members,
            "active_members": get_active_member_count(row.gym_id),
            "pricing_breakdown": calculate_gym_pricing(get_active_member_count(row.gym_id)),
        }
        for row in rows
    ]), 200



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
    gym_name = gym.name
    user_ids = db.session.execute(
        select(User.id).where(User.gym_id == gym.id)
    ).scalars().all()

    try:
        if user_ids:
            db.session.execute(
                delete(Announcement).where(
                    or_(
                        Announcement.gym_id == gym.id,
                        Announcement.author_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                delete(Attendance).where(
                    or_(
                        Attendance.client_id.in_(user_ids),
                        Attendance.trainer_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                delete(Message).where(
                    or_(
                        Message.sender_id.in_(user_ids),
                        Message.receiver_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                delete(Payment).where(
                    or_(
                        Payment.gym_id == gym.id,
                        Payment.user_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                delete(ProgressLog).where(
                    or_(
                        ProgressLog.client_id.in_(user_ids),
                        ProgressLog.trainer_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                delete(Schedule).where(
                    or_(
                        Schedule.gym_id == gym.id,
                        Schedule.client_id.in_(user_ids),
                        Schedule.trainer_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                delete(Subscription).where(
                    or_(
                        Subscription.gym_id == gym.id,
                        Subscription.user_id.in_(user_ids)
                    )
                )
            )
            db.session.execute(
                update(AuditLog)
                .where(AuditLog.user_id.in_(user_ids))
                .values(user_id=None)
            )

            plan_ids = db.session.execute(
                select(WorkoutPlan.id).where(
                    or_(
                        WorkoutPlan.gym_id == gym.id,
                        WorkoutPlan.client_id.in_(user_ids),
                        WorkoutPlan.trainer_id.in_(user_ids)
                    )
                )
            ).scalars().all()

            if plan_ids:
                day_ids = db.session.execute(
                    select(WorkoutDay.id).where(WorkoutDay.plan_id.in_(plan_ids))
                ).scalars().all()

                if day_ids:
                    db.session.execute(
                        delete(WorkoutExercise).where(
                            WorkoutExercise.day_id.in_(day_ids)
                        )
                    )

                db.session.execute(
                    delete(WorkoutDay).where(WorkoutDay.plan_id.in_(plan_ids))
                )
                db.session.execute(
                    delete(WorkoutPlan).where(WorkoutPlan.id.in_(plan_ids))
                )

            db.session.execute(delete(User).where(User.id.in_(user_ids)))

        db.session.execute(delete(GymPricing).where(GymPricing.gym_id == gym.id))
        db.session.execute(
            delete(GymSubscription).where(GymSubscription.gym_id == gym.id)
        )
        log_action(
            "delete_gym",
            entity="gym",
            entity_id=gym_id,
            details={"name": gym_name},
            session=db.session,
        )
        db.session.execute(delete(Gym).where(Gym.id == gym.id))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to delete gym %s", gym_id)
        return jsonify({"error": "Failed to delete gym"}), 500

    return jsonify({"message": "Gym deleted permanently"}), 200



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
    log_action(
        "approve_pricing",
        entity="gym_pricing",
        entity_id=pricing.id,
        details={"gym_id": pricing.gym_id},
        session=db.session,
    )
    db.session.commit()

    return {"message": f"Pricing for {pricing.gym.name} approved"}, 200


@superadmin_bp.get("/audit-logs")
@jwt_required()
@role_required("superadmin")
def get_audit_logs():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()

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


@superadmin_bp.delete("/audit-logs")
@jwt_required()
@role_required("superadmin")
def delete_audit_logs():
    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "older_than").strip().lower()

    if mode == "all":
        deleted_count = db.session.query(AuditLog).delete()
        db.session.commit()
        return jsonify({
            "message": "All audit logs deleted",
            "deleted_count": deleted_count,
        }), 200

    older_than_days = data.get("older_than_days", 30)

    try:
        older_than_days = int(older_than_days)
    except (TypeError, ValueError):
        return jsonify({"error": "older_than_days must be a number"}), 400

    if older_than_days < 1:
        return jsonify({"error": "older_than_days must be at least 1"}), 400

    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    deleted_count = (
        db.session.query(AuditLog)
        .filter(AuditLog.created_at < cutoff)
        .delete()
    )
    db.session.commit()

    return jsonify({
        "message": f"Audit logs older than {older_than_days} days deleted",
        "deleted_count": deleted_count,
    }), 200


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


@superadmin_bp.patch("/gyms/<int:gym_id>/deactivate")
@jwt_required()
@role_required("superadmin")
def deactivate_gym(gym_id):

    gym = Gym.query.get_or_404(gym_id)

    gym.status = "inactive"

    # deactivate all users
    users = User.query.filter_by(gym_id=gym.id).all()

    for user in users:
        user.is_active = False

    log_action(
        "deactivate_gym",
        entity="gym",
        entity_id=gym.id,
        details={"status": "inactive"},
        session=db.session,
    )
    db.session.commit()

    return {
        "message": "Gym deactivated"
    }, 200

@superadmin_bp.patch("/gyms/<int:gym_id>/activate")
@jwt_required()
@role_required("superadmin")
def activate_gym(gym_id):

    gym = Gym.query.get_or_404(gym_id)

    gym.status = "active"

    users = User.query.filter_by(gym_id=gym.id).all()

    for user in users:
        user.is_active = True

    log_action(
        "activate_gym",
        entity="gym",
        entity_id=gym.id,
        details={"status": "active"},
        session=db.session,
    )
    db.session.commit()

    return {
        "message": "Gym activated"
    }, 200



