from extensions import db
from datetime import datetime

class ProgressLog(db.Model):
    __tablename__ = "progress_logs"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    weight = db.Column(db.Float)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "trainer_id": self.trainer_id,
            "weight": self.weight,
            "notes": self.notes,
            "date": self.created_at.isoformat()
        }
