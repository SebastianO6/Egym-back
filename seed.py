from models import User, Gym
from extensions import db

def get_or_create(model, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    instance = model(**kwargs)
    db.session.add(instance)
    return instance

def seed():
    gym = get_or_create(Gym, name="E-Gym")

    users = [
        ("super@egym.com", "superadmin", None),
        ("admin@egym.com", "gymadmin", gym.id),
        ("trainer@egym.com", "trainer", gym.id),
        ("client@egym.com", "client", gym.id),
    ]

    for email, role, gym_id in users:
        user = get_or_create(User, email=email)
        user.role = role
        user.gym_id = gym_id
        user.set_password("password123")
        user.must_change_password = role == "gymadmin"

    db.session.commit()
    print("✅ Seed complete")
