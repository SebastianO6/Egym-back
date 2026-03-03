from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from extensions import db
from models import Announcement, Message


def cleanup_expired_announcements():
    Announcement.query.filter(
        Announcement.expires_at.isnot(None),
        Announcement.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)

    db.session.commit()


def cleanup_old_messages(days=90):
    cutoff = datetime.utcnow() - timedelta(days=days)

    Message.query.filter(
        Message.created_at < cutoff
    ).delete(synchronize_session=False)

    db.session.commit()


def start_scheduler(app):
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=cleanup_expired_announcements,
        trigger="interval",
        hours=24
    )

    scheduler.add_job(
        func=cleanup_old_messages,
        trigger="interval",
        hours=24
    )

    scheduler.start()

    # Prevent scheduler from stopping with app reload
    import atexit
    atexit.register(lambda: scheduler.shutdown())