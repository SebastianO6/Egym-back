import logging

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import join_room

from extensions import db, socketio
from models import Message


logger = logging.getLogger(__name__)
connected_users = {}


@socketio.on("connect")
def handle_connect(auth):
    try:
        if not auth or "token" not in auth:
            logger.warning("Socket connection rejected: missing auth token")
            return False

        raw_token = auth["token"].replace("Bearer ", "")
        decoded = decode_token(raw_token)
        user_id = int(decoded["sub"])
        gym_id = decoded.get("gym_id")

        connected_users[request.sid] = user_id

        if gym_id:
            join_room(f"gym_{gym_id}")

        logger.info("Socket connected for user %s", user_id)
    except Exception as exc:
        logger.warning("Socket connection rejected: %s", exc)
        return False


@socketio.on("disconnect")
def handle_disconnect():
    connected_users.pop(request.sid, None)


@socketio.on("join_room")
def handle_join(data):
    try:
        user_id = connected_users.get(request.sid)
        if not user_id:
            return

        receiver_id = int(data.get("receiver_id"))
        room = f"chat_{min(user_id, receiver_id)}_{max(user_id, receiver_id)}"
        join_room(room)
    except Exception as exc:
        logger.exception("Socket join_room failed: %s", exc)


@socketio.on("send_message")
def handle_send(data):
    try:
        sender_id = connected_users.get(request.sid)
        if not sender_id:
            logger.warning("Socket send rejected: unauthorized user")
            return

        receiver_id = int(data.get("receiver_id"))
        content = data.get("content")

        if not content:
            return

        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
        )

        db.session.add(message)
        db.session.commit()

        room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
        socketio.emit("new_message", message.to_dict(sender_id), room=room)
    except Exception as exc:
        logger.exception("Socket send_message failed: %s", exc)
