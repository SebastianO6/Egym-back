from extensions import db
from models import User


class Schedule(db.Model):
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)

    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)

    trainer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    plan_id = db.Column(db.Integer, db.ForeignKey("workout_plans.id"), nullable = False)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    status = db.Column(db.String(20), default="scheduled")

    # 🔥 Relationships (NO conflicts)
    trainer = db.relationship(
        "User",
        foreign_keys=[trainer_id],
        lazy="joined"
    )

    client = db.relationship(
        "User",
        foreign_keys=[client_id],
        lazy="joined"
    )

    plan = db.relationship("WorkoutPlan", foreign_keys=[plan_id], lazy = "joined")

    def to_dict(self):
        return {
            "id": self.id,
            "trainer_id": self.trainer_id,
            "client_id": self.client_id,
            "member_name": self.client.full_name if self.client else None,
            "workout_date": self.start_time.date().isoformat(),
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "plan_id": self.plan_id,
            "status": self.status
        }
