from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from extensions import db
from models import Announcement, Message, Subscription, User, GymSubscription, Gym




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

    # NEW
    scheduler.add_job(
        func=expire_member_subscriptions,
        trigger="interval",
        hours=24
    )

    scheduler.add_job(
        func=expire_gym_subscriptions,
        trigger="interval",
        hours=24
    )

    scheduler.start()

    import atexit
    atexit.register(lambda: scheduler.shutdown())

def expire_member_subscriptions():
    now = datetime.utcnow()

    expired_subs = Subscription.query.filter(
        Subscription.end_date < now,
        Subscription.is_active == True
    ).all()

    for sub in expired_subs:
        sub.is_active = False

        # also mark user inactive
        user = User.query.get(sub.user_id)
        if user:
            user.is_active = False

    db.session.commit()



def expire_gym_subscriptions():
    now = datetime.utcnow()
    expired = GymSubscription.query.filter(
        GymSubscription.end_date < now,
        GymSubscription.is_active == True
    ).all()

    for sub in expired:
        sub.is_active = False  # subscription is now inactive

        gym = Gym.query.get(sub.gym_id)
        if gym:
            gym.status = "inactive"  # mark gym inactive

            users = User.query.filter_by(gym_id=gym.id).all()
            for user in users:
                user.is_active = False  # all users inactive

    db.session.commit()