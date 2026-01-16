from extensions import db
from models.user import User
from models.gym import Gym

def seed():
    gym = Gym.query.filter_by(name="E-Gym Nairobi").first()
    if not gym:
        gym = Gym(name="E-Gym Nairobi", location="CBD")
        db.session.add(gym)
        db.session.commit()

    users = [
        ("superadmin@test.com", "superadmin"),
        ("admin@test.com", "gymadmin"),
        ("trainer@test.com", "trainer"),
        ("client@test.com", "client"),
    ]

    for email, role in users:
        existing = User.query.filter_by(email=email).first()
        if existing:
            continue  # 🔑 prevents duplicate error

        u = User(
            email=email,
            full_name=role.capitalize(),
            role=role,
            gym_id=gym.id
        )
        u.set_password("password123")
        db.session.add(u)

    db.session.commit()
