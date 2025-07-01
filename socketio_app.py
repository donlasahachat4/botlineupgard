from flask_socketio import SocketIO, emit
from flask_login import current_user
from bet_handler import socket_bet

socketio = SocketIO(cors_allowed_origins="*")

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        print(f"User {current_user.username} connected via Socket.IO")

@socketio.on('bet')
def on_bet(data):
    socket_bet(socketio, data)


@socketio.on('chat')
def handle_chat(data):
    """Broadcast chat messages from authenticated users."""
    if not current_user.is_authenticated:
        return
    msg = data.get('msg')
    if msg:
        socketio.emit('chat_broadcast', {
            'user': current_user.username,
            'msg': msg
        })


def emit_balance_update(user_id: int, new_balance: float) -> None:
    """Broadcast balance updates to all connected clients."""
    socketio.emit('balance_update', {'user_id': user_id, 'new_balance': new_balance}, broadcast=True)


def emit_admin_notify(event: dict) -> None:
    """Send a notification event to admin clients."""
    socketio.emit('notify_admin', event, namespace='/admin', broadcast=True)

