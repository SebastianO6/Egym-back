from app import create_app
from extensions import db
import models  # noqa: F401
from models import User


def seed(create_tables=True):
    app = create_app()

    with app.app_context():
        if create_tables:
            db.create_all()

        print("Seeding database...")

        existing = User.query.filter_by(email="superadmin@egym.com").first()

        if not existing:
            superadmin = User(
                email="superadmin@egym.com",
                role="superadmin",
                is_active=True,
            )
            superadmin.set_password("Admin123!")
            db.session.add(superadmin)
            db.session.commit()
            print("Superadmin created")
        else:
            print("Superadmin already exists")

        print("Seeding complete")


if __name__ == "__main__":
    seed()
