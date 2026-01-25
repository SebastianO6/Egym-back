from extensions import db
from datetime import datetime

class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)

    plan = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)

    is_active = db.Column(db.Boolean, default=True)
