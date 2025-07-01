from datetime import datetime, timedelta
import random
import string
from models import db, OTPRequest


def generate_code() -> str:
    """Return a random 6 digit code."""
    return ''.join(random.choices(string.digits, k=6))


def create_otp(user_id: int) -> str:
    """Create an OTP for given user valid for 5 minutes."""
    code = generate_code()
    otp = OTPRequest(
        user_id=user_id,
        code=code,
        valid_until=datetime.utcnow() + timedelta(minutes=5),
        is_verified=False,
    )
    db.session.add(otp)
    db.session.commit()
    return code


def verify_otp(user_id: int, code: str) -> bool:
    otp = (
        OTPRequest.query.filter_by(user_id=user_id, code=code, is_verified=False)
        .first()
    )
    if otp and otp.valid_until > datetime.utcnow():
        otp.is_verified = True
        db.session.commit()
        return True
    return False
