from extensions import db
from datetime import datetime

class WorkoutPlan(db.Model):
    __tablename__ = "workout_plans"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"))

    client = db.relationship("User", foreign_keys=[client_id], lazy="joined")

    workout_days = db.relationship(
        "WorkoutDay",
        backref="plan",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    trainer = db.relationship("User", foreign_keys=[trainer_id], lazy="joined")  


    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "client_id": self.client_id,
            "trainer_id": self.trainer_id,
            "client_name": self.client.full_name if self.client else None,
            "trainer_name": self.trainer.full_name if self.trainer else None
        }


