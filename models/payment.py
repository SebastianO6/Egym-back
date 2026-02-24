from extensions import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(30))
    status = db.Column(db.String(20), default="paid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount),
            "method": self.method,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

