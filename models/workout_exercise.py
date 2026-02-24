from extensions import db

class WorkoutExercise(db.Model):
    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("workout_days.id"), nullable=False)
    name = db.Column(db.String(255))
    sets = db.Column(db.String(50))
    reps = db.Column(db.String(50))
    rest = db.Column(db.String(50))

