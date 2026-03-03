from datetime import datetime
from extensions import db
from models import Announcement

def cleanup_expired_announcements():
    (
        Announcement.query
        .filter(
            Announcement.expires_at.isnot(None),
            Announcement.expires_at < datetime.utcnow()
        )
        .delete(synchronize_session=False)
    )

    db.session.commit()