from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from decorators import role_required
from extensions import db
from models import Message, Client

messages_bp = Blueprint("messages", __name__)

# ---------------- SEND MESSAGE ----------------

@messages_bp.post("/messages")
@role_required("trainer", "client")
def send_message():
    sender_id = int(get_jwt_identity())
    claims = get_jwt()
    data = request.json

    # Trainer → Client validation
    if claims["role"] == "trainer":
        client = Client.query.filter_by(
            id=data["receiver_id"],
            trainer_id=sender_id
        ).first_or_404()

    msg = Message(
        sender_id=sender_id,
        receiver_id=data["receiver_id"],
        content=data["content"]
    )

    db.session.add(msg)
    db.session.commit()

    return jsonify({"message": "Sent"}), 201

# ---------------- FETCH CONVERSATION ----------------

@messages_bp.get("/messages/<int:user_id>")
@role_required("trainer", "client")
def conversation(user_id):
    me = int(get_jwt_identity())

    messages = Message.query.filter(
        ((Message.sender_id == me) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == me))
    ).order_by(Message.created_at).all()

    return jsonify([
        {
            "from": m.sender_id,
            "to": m.receiver_id,
            "content": m.content,
            "created_at": m.created_at,
            "read": m.is_read
        }
        for m in messages
    ])
