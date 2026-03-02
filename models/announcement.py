from extensions import db
from datetime import datetime


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(50), default="general")
    gym_id = db.Column(db.Integer, db.ForeignKey("gyms.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    expires_at = db.Column(db.DateTime, nullable = True )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "tag": self.tag,
            "gym_id": self.gym_id,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
