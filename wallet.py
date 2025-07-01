from models import db, Wallet, WalletLog


def credit_wallet(user_id: int, amount: float, source: str = "system") -> Wallet:
    wallet = Wallet.query.filter_by(owner_id=str(user_id)).first()
    if not wallet:
        wallet = Wallet(owner_id=str(user_id), balance=0, channel='web')
        db.session.add(wallet)
    wallet.balance += amount
    db.session.add(
        WalletLog(
            user_id=str(user_id),
            action='deposit',
            amount=amount,
            status='success',
            platform=source,
        )
    )
    db.session.commit()
    return wallet
