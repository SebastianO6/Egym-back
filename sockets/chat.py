from flask_socketio import emit, join_room
from flask import request
from flask_jwt_extended import decode_token
from extensions import socketio, db
from models import Message

connected_users = {}

@socketio.on("connect")
def handle_connect(auth):
    try:
        if not auth or "token" not in auth:
            print("❌ No auth token provided")
            return False

        raw_token = auth["token"].replace("Bearer ", "")
        decoded = decode_token(raw_token)
        user_id = int(decoded["sub"])

        connected_users[request.sid] = user_id
        print(f"✅ User {user_id} connected")

    except Exception as e:
        print("❌ Invalid token:", str(e))
        return False


@socketio.on("disconnect")
def handle_disconnect():
    connected_users.pop(request.sid, None)


@socketio.on("join_room")
def handle_join(data):
    try:
        user_id = connected_users.get(request.sid)
        receiver_id = int(data.get("receiver_id"))

        room = f"chat_{min(user_id, receiver_id)}_{max(user_id, receiver_id)}"
        join_room(room)

        print(f"📌 {user_id} joined {room}")

    except Exception as e:
        print("JOIN ERROR:", e)


@socketio.on("send_message")
def handle_send(data):
    try:
        sender_id = connected_users.get(request.sid)
        if not sender_id:
            print("❌ Unauthorized socket user")
            return

        receiver_id = int(data.get("receiver_id"))
        content = data.get("content")

        if not content:
            return

        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )

        db.session.add(message)
        db.session.commit()

        room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"

        socketio.emit(
            "new_message",
            message.to_dict(sender_id),
            room=room
        )

        print("✅ Message emitted")

    except Exception as e:
        print("❌ SEND ERROR:", str(e))