# utils/auth.py
from flask_jwt_extended import get_jwt_identity
from flask import abort
from models.user import User
from datetime import timedelta, datetime
import secrets
from extensions import db


def get_current_user():
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return User.query.get(int(user_id))


def current_admin():
    admin = User.query.get_or_404(get_jwt_identity())
    if not admin.gym_id:
        abort(403, "Gym not assigned")
    return admin


def invite_user(email, role, gym_id):
    existing = User.query.filter_by(email=email).first()
    if existing:
        abort(400, "User with this email already exists")

    token = secrets.token_urlsafe(32)

    user = User(
        email=email,
        role=role,
        gym_id=gym_id,
        is_active=False,                # 🔴 IMPORTANT
        invite_token=token,
        invite_expires_at=datetime.utcnow() + timedelta(hours=24),
        password_hash=None,
        must_change_password=False
    )

    db.session.add(user)
    db.session.commit()

    return token


