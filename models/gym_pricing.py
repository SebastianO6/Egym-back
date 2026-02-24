from extensions import db
from datetime import datetime

class GymPricing(db.Model):
    __tablename__ = "gym_pricing"

    id = db.Column(db.Integer, primary_key=True)

    gym_id = db.Column(
        db.Integer,
        db.ForeignKey("gyms.id"),
        unique=True,
        nullable=False
    )

    daily_price = db.Column(db.Numeric(10, 2), nullable=False)
    monthly_price = db.Column(db.Numeric(10, 2), nullable=False)

    approved = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    gym = db.relationship("Gym", backref = "pricing", lazy =True)
