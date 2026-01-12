from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from datetime import datetime

from decorators import role_required
from extensions import db
from models import User, Trainer, Client, Payment, Announcement

gymadmin_bp = Blueprint("gymadmin", __name__)

# ---------------- DASHBOARD ----------------

@gymadmin_bp.get("/gymadmin/dashboard")
@role_required("gymadmin")
def dashboard():
    claims = get_jwt()
    gym_id = claims["gym_id"]

    clients = Client.query.filter_by(gym_id=gym_id).count()
    trainers = Trainer.query.filter_by(gym_id=gym_id).count()

    revenue = (
        db.session.query(func.sum(Payment.amount))
        .join(Client, Client.id == Payment.client_id)
        .filter(Client.gym_id == gym_id)
        .scalar()
    ) or 0

    return jsonify({
        "clients": clients,
        "trainers": trainers,
        "revenue": revenue
    })

# ---------------- TRAINERS ----------------

@gymadmin_bp.post("/gymadmin/trainers")
@role_required("gymadmin")
def create_trainer():
    claims = get_jwt()
    gym_id = claims["gym_id"]
    data = request.json

    trainer_user = User(
        email=data["email"],
        password=generate_password_hash(data["password"]),
        role="trainer",
        gym_id=gym_id
    )
    db.session.add(trainer_user)
    db.session.commit()

    trainer = Trainer(
        user_id=trainer_user.id,
        gym_id=gym_id
    )
    db.session.add(trainer)
    db.session.commit()

    return jsonify({"message": "Trainer created"}), 201


@gymadmin_bp.get("/gymadmin/trainers")
@role_required("gymadmin")
def list_trainers():
    claims = get_jwt()
    gym_id = claims["gym_id"]

    trainers = (
        db.session.query(Trainer, User)
        .join(User, Trainer.user_id == User.id)
        .filter(Trainer.gym_id == gym_id)
        .all()
    )

    return jsonify([
        {
            "trainer_id": t.id,
            "email": u.email,
            "active": u.is_active
        }
        for t, u in trainers
    ])

# ---------------- CLIENTS ----------------

@gymadmin_bp.post("/gymadmin/clients")
@role_required("gymadmin")
def create_client():
    claims = get_jwt()
    gym_id = claims["gym_id"]
    data = request.json

    client_user = User(
        email=data["email"],
        password=generate_password_hash(data["password"]),
        role="client",
        gym_id=gym_id
    )
    db.session.add(client_user)
    db.session.commit()

    client = Client(
        user_id=client_user.id,
        gym_id=gym_id,
        trainer_id=data.get("trainer_id"),
        subscription_active=data.get("subscription_active", False)
    )
    db.session.add(client)
    db.session.commit()

    return jsonify({"message": "Client created"}), 201


@gymadmin_bp.get("/gymadmin/clients")
@role_required("gymadmin")
def list_clients():
    claims = get_jwt()
    gym_id = claims["gym_id"]

    clients = (
        db.session.query(Client, User)
        .join(User, Client.user_id == User.id)
        .filter(Client.gym_id == gym_id)
        .all()
    )

    return jsonify([
        {
            "client_id": c.id,
            "email": u.email,
            "trainer_id": c.trainer_id,
            "subscription_active": c.subscription_active,
            "active": u.is_active
        }
        for c, u in clients
    ])

# ---------------- ASSIGN TRAINER ----------------

@gymadmin_bp.put("/gymadmin/clients/<int:client_id>/assign-trainer")
@role_required("gymadmin")
def assign_trainer(client_id):
    claims = get_jwt()
    gym_id = claims["gym_id"]
    data = request.json

    client = Client.query.filter_by(
        id=client_id,
        gym_id=gym_id
    ).first_or_404()

    trainer = Trainer.query.filter_by(
        id=data["trainer_id"],
        gym_id=gym_id
    ).first_or_404()

    client.trainer_id = trainer.id
    db.session.commit()

    return jsonify({"message": "Trainer assigned"})

# ---------------- SUSPEND / ACTIVATE CLIENT ----------------

@gymadmin_bp.put("/gymadmin/clients/<int:client_id>/status")
@role_required("gymadmin")
def toggle_client_status(client_id):
    claims = get_jwt()
    gym_id = claims["gym_id"]

    client, user_obj = (
        db.session.query(Client, User)
        .join(User, Client.user_id == User.id)
        .filter(Client.id == client_id, Client.gym_id == gym_id)
        .first_or_404()
    )

    user_obj.is_active = not user_obj.is_active
    db.session.commit()

    return jsonify({"active": user_obj.is_active})

# ---------------- PAYMENTS ----------------

@gymadmin_bp.get("/gymadmin/payments")
@role_required("gymadmin")
def gym_payments():
    claims = get_jwt()
    gym_id = claims["gym_id"]

    payments = (
        db.session.query(Payment, Client, User)
        .join(Client, Payment.client_id == Client.id)
        .join(User, Client.user_id == User.id)
        .filter(Client.gym_id == gym_id)
        .all()
    )

    return jsonify([
        {
            "client_email": u.email,
            "amount": p.amount,
            "status": p.status,
            "paid_at": p.paid_at
        }
        for p, c, u in payments
    ])

# ---------------- ANNOUNCEMENTS ----------------

@gymadmin_bp.post("/gymadmin/announcements")
@role_required("gymadmin")
def create_announcement():
    claims = get_jwt()
    gym_id = claims["gym_id"]
    data = request.json

    ann = Announcement(
        gym_id=gym_id,
        title=data["title"],
        message=data["message"]
    )
    db.session.add(ann)
    db.session.commit()

    return jsonify({"message": "Announcement created"}), 201


@gymadmin_bp.get("/gymadmin/announcements")
@role_required("gymadmin")
def get_announcements():
    claims = get_jwt()
    gym_id = claims["gym_id"]

    anns = (
        Announcement.query
        .filter_by(gym_id=gym_id)
        .order_by(Announcement.created_at.desc())
        .all()
    )

    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at
        }
        for a in anns
    ])

@gymadmin_bp.post("/gymadmin/payments")
@role_required("gymadmin")
def add_payment():
    claims = get_jwt()
    gym_id = claims["gym_id"]
    data = request.json

    client = Client.query.filter_by(
        id=data["client_id"],
        gym_id=gym_id
    ).first_or_404()

    payment = Payment(
        client_id=client.id,
        amount=data["amount"],
        status=data["status"],
        paid_at=datetime.utcnow() if data["status"] == "paid" else None
    )

    if data["status"] == "paid":
        client.subscription_active = True

    db.session.add(payment)
    db.session.commit()

    return jsonify({"message": "Payment recorded"}), 201
