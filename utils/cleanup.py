from datetime import datetime
from extensions import db
from models import Announcement


def cleanup_expired_announcements():
    expired = Announcement.query.filter(
        Announcement.expires_at.isnot(None),
        Announcement.expires_at < datetime.utcnow()
    ).all()

    for ann in expired:
        db.session.delete(ann)

    db.session.commit()