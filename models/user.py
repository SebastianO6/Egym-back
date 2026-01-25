from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # -------- Identity --------
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)

    # -------- Role --------
    role = db.Column(db.String(30), nullable=False)  # superadmin | gymadmin | trainer | client
    is_active = db.Column(db.Boolean, default=False)

    # -------- Relations --------
    gym_id = db.Column(
        db.Integer,
        db.ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=True
    )

    trainer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    # -------- Invite Flow --------

    invite_token = db.Column(db.String(255), unique=True, nullable=True, index=True)
    invite_expires_at = db.Column(db.DateTime, nullable=True)

    # -------- Security --------
    must_change_password = db.Column(db.Boolean, default=False)

    # -------- Audit --------
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # -------- Relationships --------
    gym = db.relationship("Gym", back_populates="users", foreign_keys=[gym_id])
    trainer = db.relationship("User", remote_side=[id])

    # -------- Password helpers --------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "gym_id": self.gym_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }
