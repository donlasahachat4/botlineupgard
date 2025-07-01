from datetime import timedelta, datetime
from models import db, DepositPending, DepositNotification, Wallet


def match_deposit_notification(notif: DepositNotification):
    """Try to match a deposit notification with a pending deposit."""
    deposit = DepositPending.query.filter(
        DepositPending.status == 'pending',
        DepositPending.amount == notif.amount,
        DepositPending.created_at >= notif.received_at - timedelta(hours=1),
        DepositPending.created_at <= notif.received_at + timedelta(hours=1)
    ).first()
    if deposit:
        deposit.status = 'matched'
        notif.matched = True
        notif.matched_deposit_id = deposit.id
        wallet = Wallet.query.filter_by(owner_id=deposit.user_id).first()
        if wallet:
            wallet.balance += notif.amount
        db.session.add_all([deposit, notif, wallet])
        db.session.commit()
        return True, deposit.id
    db.session.add(notif)
    db.session.commit()
    return False, None
