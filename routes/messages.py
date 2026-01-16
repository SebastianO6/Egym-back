from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from routes.decorators import role_required
from extensions import db
from models import Message, User

messages_bp = Blueprint("messages", __name__, url_prefix="/api/messages")

# ---------------- SEND MESSAGE ----------------

@messages_bp.post("")
@role_required("trainer", "client")
def send_message():
    sender_id = int(get_jwt_identity())
    claims = get_jwt()
    data = request.json

    receiver = User.query.get_or_404(data["receiver_id"])

    # Optional safety: trainer can only message clients in same gym
    if claims["role"] == "trainer":
        if receiver.role != "client" or receiver.gym_id != claims.get("gym_id"):
            return jsonify({"error": "Not allowed"}), 403

    msg = Message(
        sender_id=sender_id,
        receiver_id=receiver.id,
        content=data["content"]
    )

    db.session.add(msg)
    db.session.commit()

    return jsonify({"message": "Sent"}), 201


# ---------------- FETCH CONVERSATION ----------------

@messages_bp.get("/<int:user_id>")
@role_required("trainer", "client")
def conversation(user_id):
    me = int(get_jwt_identity())

    messages = Message.query.filter(
        ((Message.sender_id == me) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == me))
    ).order_by(Message.created_at.asc()).all()

    return jsonify({
        "items": [
            {
                "from": m.sender_id,
                "to": m.receiver_id,
                "content": m.content,
                "created_at": m.created_at
            }
            for m in messages
        ]
    })
