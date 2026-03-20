import math

from models import User


BASE_PRICE = 10000
BASE_MEMBER_LIMIT = 50
MEMBERS_PER_TIER = 50
TIER_PRICE = 10000


def calculate_gym_pricing(member_count):
    safe_member_count = max(int(member_count or 0), 0)
    extra_members = max(safe_member_count - BASE_MEMBER_LIMIT, 0)
    extra_tiers = math.ceil(extra_members / MEMBERS_PER_TIER) if extra_members else 0
    extra_cost = extra_tiers * TIER_PRICE
    final_price = BASE_PRICE + extra_cost

    return {
        "member_count": safe_member_count,
        "base_price": BASE_PRICE,
        "base_member_limit": BASE_MEMBER_LIMIT,
        "extra_members": extra_members,
        "members_per_tier": MEMBERS_PER_TIER,
        "extra_tiers": extra_tiers,
        "tier_price": TIER_PRICE,
        "extra_cost": extra_cost,
        "final_price": final_price,
    }


def get_active_member_count(gym_id):
    return User.query.filter_by(
        gym_id=gym_id,
        role="client",
        is_active=True,
    ).count()
