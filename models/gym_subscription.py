# models/gym_subscription.py
from extensions import db
from datetime import datetime

class GymSubscription(db.Model):
    __tablename__ = "gym_subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)

    plan = db.Column(db.String(20))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "gym_id": self.gym_id,
            "plan": self.plan,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "is_active": self.is_active
        }