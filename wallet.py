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


def get_user_wallet(user_id: int) -> Wallet:
    """Return wallet for a user, creating if missing."""
    wallet = Wallet.query.filter_by(owner_id=str(user_id)).first()
    if not wallet:
        wallet = Wallet(owner_id=str(user_id), balance=0, channel='web')
        db.session.add(wallet)
        db.session.commit()
    return wallet


def update_wallet_balance(user_id: int, delta: float) -> float:
    """Adjust wallet balance by delta and return new balance."""
    wallet = get_user_wallet(user_id)
    wallet.balance += delta
    db.session.commit()
    return float(wallet.balance)
