from extensions import db
from datetime import datetime


class Gym(db.Model):
    __tablename__ = "gyms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    slug = db.Column(db.String(120), unique=True)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship(
        "User",
        back_populates="gym",
        cascade="all, delete",
        passive_deletes=True        
    )

    subscriptions = db.relationship(
        "GymSubscription",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    pricing = db.relationship(
        "GymPricing",
        back_populates="gym",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True
    )

    payments = db.relationship(
        "Payment",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
