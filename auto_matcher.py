from datetime import datetime
import re
from models import User


def auto_matcher(payload: dict):
    """Simple heuristic to extract user and amount from a payload."""
    msg = str(payload)
    m = re.search(r'จำนวน\s*([\d,]+\.\d{2})\s*บาท', msg)
    amount = float(m.group(1).replace(',', '')) if m else None
    user_hint = payload.get('user') or payload.get('account')
    user = None
    if user_hint:
        user = User.query.filter((User.phone == user_hint) | (User.line_user_id == user_hint)).first()
    return (user is not None and amount is not None), user, amount
