from extensions import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(30))  # mpesa, cash, card
    status = db.Column(db.String(20), default="paid")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
