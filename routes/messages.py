# routes/messages.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db, socketio
from models import Message  

messages_bp = Blueprint("messages", __name__)

@messages_bp.get("/conversation/<int:partner_id>")
@jwt_required()
def get_conversation(partner_id):
    user_id = int(get_jwt_identity())

    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.receiver_id == user_id))
    ).order_by(Message.created_at.asc()).all()

    return jsonify({
        "items": [m.to_dict(user_id) for m in messages]
    })

@messages_bp.post("/send")
@jwt_required()
def send_message():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    receiver_id = int(data.get("receiver_id"))
    content = data.get("content")

    if not content:
        return jsonify({"error": "Missing content"}), 400

    message = Message(
        sender_id=user_id,
        receiver_id=receiver_id,
        content=content
    )

    db.session.add(message)
    db.session.commit()

    room = f"chat_{min(user_id, receiver_id)}_{max(user_id, receiver_id)}"

    socketio.emit(
        "new_message",
        message.to_dict(user_id),
        room=room
    )

    return jsonify(message.to_dict(user_id)), 201   