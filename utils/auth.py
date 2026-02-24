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








