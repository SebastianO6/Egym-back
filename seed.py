from extensions import db
from models import Gym, User
from datetime import datetime
import secrets


def seed():
    print("🌱 Seeding database...")

    # SUPERADMIN
    if not User.query.filter_by(email="superadmin@egym.com").first():
        sa = User(
            email="superadmin@egym.com",
            role="superadmin",
            is_active=True
        )
        sa.set_password("Admin123!")
        db.session.add(sa)

    # GYM
    gym = Gym.query.filter_by(name="Demo Gym").first()
    if not gym:
        gym = Gym(name="Demo Gym", phone="0700000000", address="Nairobi")
        db.session.add(gym)
        db.session.flush()

    # GYM ADMIN (INVITED)
    if not User.query.filter_by(email="C").first():
        admin = User(
            email="admin@demogym.com",
            role="gymadmin",
            gym_id=gym.id,
            invite_token=secrets.token_urlsafe(32),
            invite_expires_at=datetime.utcnow()
        )
        db.session.add(admin)

    # TRAINER
    if not User.query.filter_by(email="trainer@demogym.com").first():
        trainer = User(
            email="trainer@demogym.com",
            role="trainer",
            gym_id=gym.id,
            is_active=True
        )
        trainer.set_password("Trainer123!")
        db.session.add(trainer)

    # CLIENT
    if not User.query.filter_by(email="client@demogym.com").first():
        client = User(
            email="client@demogym.com",
            role="client",
            gym_id=gym.id,
            is_active=True
        )
        client.set_password("Client123!")
        db.session.add(client)

    db.session.commit()
    print("✅ Seeding complete")
