from extensions import db

class WorkoutDay(db.Model):
    __tablename__ = "workout_days"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    plan_id = db.Column(db.Integer, db.ForeignKey("workout_plans.id"), nullable=False)

    exercises = db.relationship(
        "WorkoutExercise",
        backref="day",
        lazy=True
    )

