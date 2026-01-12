from extensions import db
from models import Gym, User, Trainer, Client, Payment, WorkoutPlan
from werkzeug.security import generate_password_hash
from datetime import datetime

def seed():
    # ---------------- GYM ----------------
    gym = Gym.query.filter_by(name="Demo Gym").first()
    if not gym:
        gym = Gym(name="Demo Gym", location="Nairobi")
        db.session.add(gym)
        db.session.commit()

    # ---------------- USERS ----------------
    users_data = [
        {"email": "super@egym.com", "password": "admin123", "role": "superadmin", "gym_id": None},
        {"email": "admin@egym.com", "password": "admin123", "role": "gymadmin", "gym_id": gym.id},
        {"email": "trainer@egym.com", "password": "trainer123", "role": "trainer", "gym_id": gym.id},
        {"email": "client@egym.com", "password": "client123", "role": "client", "gym_id": gym.id},
    ]

    users = {}
    for udata in users_data:
        user = User.query.filter_by(email=udata["email"]).first()
        if not user:
            user = User(
                email=udata["email"],
                password=generate_password_hash(udata["password"]),
                role=udata["role"],
                gym_id=udata["gym_id"]
            )
            db.session.add(user)
            db.session.commit()
        users[udata["role"]] = user

    # ---------------- TRAINER ----------------
    trainer = Trainer.query.filter_by(user_id=users["trainer"].id).first()
    if not trainer:
        trainer = Trainer(user_id=users["trainer"].id, gym_id=gym.id)
        db.session.add(trainer)
        db.session.commit()

    # ---------------- CLIENT ----------------
    client = Client.query.filter_by(user_id=users["client"].id).first()
    if not client:
        client = Client(
            user_id=users["client"].id,
            gym_id=gym.id,
            trainer_id=trainer.id,
            subscription_active=True
        )
        db.session.add(client)
        db.session.commit()

    # ---------------- PAYMENT ----------------
    payment = Payment.query.filter_by(client_id=client.id).first()
    if not payment:
        payment = Payment(
            client_id=client.id,
            amount=100.0,
            status="paid",
            paid_at=datetime.utcnow()
        )
        db.session.add(payment)
        db.session.commit()

    # ---------------- WORKOUT PLAN ----------------
    plan = WorkoutPlan.query.filter_by(client_id=client.id).first()
    if not plan:
        plan = WorkoutPlan(
            trainer_id=trainer.id,
            client_id=client.id,
            title="Full Body Starter Plan",
            description="Day 1: Upper body, Day 2: Lower body, Day 3: Rest..."
        )
        db.session.add(plan)
        db.session.commit()

    print("✅ Database seeded successfully (safe to run multiple times)")
