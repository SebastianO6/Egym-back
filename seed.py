from extensions import db
from models import User

def seed():
    print("🌱 Seeding database...")

    existing = User.query.filter_by(email="superadmin@egym.com").first()

    if not existing:
        superadmin = User(
            email="superadmin@egym.com",
            role="superadmin",
            is_active=True
        )
        superadmin.set_password("Admin123!")
        db.session.add(superadmin)
        db.session.commit()
        print("✅ Superadmin created")
    else:
        print("⚠️ Superadmin already exists")

    print("🌱 Seeding complete")