from extensions import db
from datetime import datetime


class Gym(db.Model):
    __tablename__ = "gyms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship(
        "User",
        back_populates="gym",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
