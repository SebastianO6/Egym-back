from datetime import datetime
from models.gym_subscription import GymSubscription


def gym_subscription_valid(gym_id):

    sub = (
        GymSubscription.query
        .filter(
            GymSubscription.gym_id == gym_id,
            GymSubscription.end_date >= datetime.utcnow()
        )
        .order_by(GymSubscription.end_date.desc())
        .first()
    )

    return sub is not None