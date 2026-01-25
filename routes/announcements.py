from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.announcement import Announcement
from models.user import User
from routes.decorators import role_required

announcements_bp = Blueprint(
    "announcements",
    __name__,
    url_prefix="/api/announcements"
)

@announcements_bp.post("/")
@jwt_required()
@role_required("superadmin", "gymadmin")
def create_announcement():
    data = request.get_json() or {}
    user = User.query.get(int(get_jwt_identity()))

    if not data.get("title") or not data.get("message"):
        return jsonify({"error": "Title and message required"}), 400

    announcement = Announcement(
        title=data["title"],
        message=data["message"],
        gym_id=user.gym_id,
        author_id=user.id
    )

    db.session.add(announcement)
    db.session.commit()

    return jsonify({"message": "Announcement created"}), 201


@announcements_bp.get("/")
@jwt_required()
def list_announcements():
    user = User.query.get(int(get_jwt_identity()))

    announcements = Announcement.query.filter_by(
        gym_id=user.gym_id
    ).order_by(Announcement.created_at.desc()).all()

    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at.isoformat()
        }
        for a in announcements
    ])
