from datetime import datetime
from models import db, DepositRequest
from wallet import credit_wallet
from utils.line_helper import push_message_to_line
from integrated_web import socketio


def match_deposit(amount: float, account: str | None = None) -> bool:
    """Attempt to match incoming deposit to pending requests."""
    now = datetime.utcnow()
    req = (
        DepositRequest.query.filter(
            DepositRequest.full_amount == amount,
            DepositRequest.status == 'pending',
            DepositRequest.expires_at > now,
        )
        .first()
    )
    if not req:
        return False

    req.status = 'matched'
    wallet = credit_wallet(req.user_id, float(req.full_amount), source='system')
    db.session.commit()
    push_message_to_line(
        f"ยอดเงินเข้าบัญชี {req.full_amount:.2f} ของผู้ใช้ {req.user_id}"
    )
    socketio.emit(
        "wallet_update",
        {"user_id": req.user_id, "balance": float(wallet.balance)},
        broadcast=True,
    )
    return True
