from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import Announcement


announcements_bp = Blueprint(
    "announcements",
    __name__,
    url_prefix="/api/announcements"
)


@announcements_bp.get("")
@jwt_required()
def list_announcements():
    
    gym_id = get_jwt().get("gym_id")

    anns = Announcement.query.filter_by(
        gym_id=gym_id
    ).order_by(
        Announcement.created_at.desc()
    ).all()

    return jsonify({
        "items": [a.to_dict() for a in anns]
    })
