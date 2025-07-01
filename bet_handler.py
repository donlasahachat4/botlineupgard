from datetime import datetime

from flask_socketio import emit
from flask import request
from flask_login import current_user

from models import db, Bet
from wallet_utils import adjust_wallet_atomic


def socket_bet(socketio, data):
    """Process a bet event from Socket.IO."""
    if not current_user.is_authenticated:
        emit('bet_error', {'msg': 'กรุณาเข้าสู่ระบบ'}, to=request.sid)
        return

    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        emit('bet_error', {'msg': 'ข้อมูลไม่ถูกต้อง'}, to=request.sid)
        return
    side = data.get('side')
    if amount <= 0 or not side:
        emit('bet_error', {'msg': 'ข้อมูลไม่ถูกต้อง'}, to=request.sid)
        return

    success, result = adjust_wallet_atomic(current_user.id, -amount, 'bet', note=f'Bet on {side}')
    if not success:
        emit('bet_error', {'msg': result}, to=request.sid)
        return
    bet = Bet(
        user_id=current_user.id,
        round_id=None,
        side=side,
        amount=amount,
        status='pending',
        created_at=datetime.utcnow(),
    )
    db.session.add(bet)
    db.session.commit()

    emit(
        'bet_placed',
        {
            'username': current_user.username,
            'amount': amount,
            'side': side,
            'time': bet.created_at.strftime('%H:%M'),
            'balance': result,
        },
        room=request.sid,
    )
    socketio.emit(
        'new_bet',
        {'user': current_user.username, 'amount': amount, 'side': side},
        broadcast=True,
    )
    emit('balance_update', {'balance': result}, room=request.sid)
