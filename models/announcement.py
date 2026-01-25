from extensions import db
from datetime import datetime


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(50), default="general")

    gym_id = db.Column(
        db.Integer,
        db.ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
