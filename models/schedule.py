from extensions import db

class Schedule(db.Model):
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)

    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="scheduled")
