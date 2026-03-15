from extensions import db
from datetime import datetime

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id",ondelete="CASCADE"), nullable=False)

    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


    __table_args__ = (
        db.Index("idx_chat_lookup", "sender_id", "receiver_id", "created_at"),
    )

    def to_dict(self, current_user_id):
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.utcnow().isoformat(),
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "is_mine": self.sender_id == current_user_id
        }