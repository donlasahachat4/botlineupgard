from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from models import db, Wallet, WalletLog, TransactionLock


def lock_wallet(user_id: int) -> bool:
    """Attempt to place a DB lock row for a wallet."""
    if TransactionLock.query.filter_by(user_id=user_id).first():
        return False
    db.session.add(TransactionLock(user_id=user_id, locked_at=datetime.utcnow()))
    db.session.commit()
    return True


def unlock_wallet(user_id: int) -> None:
    TransactionLock.query.filter_by(user_id=user_id).delete()
    db.session.commit()


def adjust_wallet_atomic(user_id: int, amount: float, action: str, note: str = ""):
    """Adjust wallet balance atomically using DB row locks."""
    try:
        if not lock_wallet(user_id):
            return False, "ธุรกรรมก่อนหน้ายังไม่เสร็จ กรุณารอ..."
        wallet = Wallet.query.filter_by(owner_id=user_id).with_for_update().first()
        if not wallet or wallet.balance + amount < 0:
            unlock_wallet(user_id)
            return False, "ยอดเงินไม่พอ"
        wallet.balance += amount
        wallet.last_updated = datetime.utcnow()
        db.session.add(
            WalletLog(
                user_id=user_id,
                action=action,
                amount=amount,
                balance_after=float(wallet.balance),
                note=note,
                created_at=datetime.utcnow(),
            )
        )
        db.session.commit()
        unlock_wallet(user_id)
        return True, float(wallet.balance)
    except SQLAlchemyError:
        db.session.rollback()
        unlock_wallet(user_id)
        return False, "ข้อผิดพลาดทางเทคนิค"
