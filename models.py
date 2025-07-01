from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Initialize SQLAlchemy instance

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), unique=True)
    line_user_id = db.Column(db.String(64), unique=True)
    is_linked = db.Column(db.Boolean, default=False)
    verify_token = db.Column(db.String(64))
    registered_ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    def get_id(self):  # type: ignore[override]
        return str(self.id)

class Wallet(db.Model):
    __tablename__ = 'wallets'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.String(64), nullable=False)
    balance = db.Column(db.Numeric(10, 2), default=0)
    locked = db.Column(db.Boolean, default=False)
    channel = db.Column(db.Enum('web', 'line', 'shared'), nullable=False)
    last_updated = db.Column(db.DateTime, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class OTPRequest(db.Model):
    """Store OTP codes for sensitive actions."""
    __tablename__ = 'otp_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    valid_until = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

class Round(db.Model):
    __tablename__ = 'rounds'
    id = db.Column(db.Integer, primary_key=True)
    red_odds = db.Column(db.Numeric(5, 2))
    blue_odds = db.Column(db.Numeric(5, 2))
    result = db.Column(db.Enum('red', 'blue'))
    status = db.Column(db.Enum('open', 'closed', 'settled'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class Bet(db.Model):
    __tablename__ = 'bets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey('rounds.id'), nullable=False)
    side = db.Column(db.Enum('red', 'blue'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum('pending', 'win', 'lose', 'cancel'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class Deposit(db.Model):
    __tablename__ = 'deposits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    slip_path = db.Column(db.String(255))
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class Withdrawal(db.Model):
    __tablename__ = 'withdrawals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    bank_name = db.Column(db.String(64))
    bank_account = db.Column(db.String(64))
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class Stream(db.Model):
    __tablename__ = 'streams'
    id = db.Column(db.Integer, primary_key=True)
    hls_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class BetLog(db.Model):
    __tablename__ = 'bet_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64))
    round_id = db.Column(db.Integer)
    side = db.Column(db.Enum('red', 'blue'))
    amount = db.Column(db.Numeric(10, 2))
    platform = db.Column(db.Enum('web', 'line'))
    status = db.Column(db.Enum('success', 'failed', 'rejected'))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class WalletLog(db.Model):
    __tablename__ = 'wallet_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    action = db.Column(db.Enum('deposit', 'withdraw'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum('pending', 'success', 'failed', 'rejected'), nullable=False)
    platform = db.Column(db.Enum('web', 'line', 'admin'), nullable=False)
    slip_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(64))
    action_type = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class SecurityLog(db.Model):
    __tablename__ = 'security_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64))
    event_type = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(10), nullable=False)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())


class DepositRequest(db.Model):
    """Pending PromptPay deposit QR requests."""
    __tablename__ = 'deposit_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    decimal = db.Column(db.Numeric(4, 2), nullable=False)
    full_amount = db.Column(db.Numeric(10, 2), nullable=False)
    ref = db.Column(db.String(64), unique=True)
    status = db.Column(db.Enum('pending', 'matched', 'expired', 'cancelled'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    expires_at = db.Column(db.DateTime)


class RegisteredBankAccount(db.Model):
    __tablename__ = 'registered_bank_accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    account_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawal_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, processing, done, failed
