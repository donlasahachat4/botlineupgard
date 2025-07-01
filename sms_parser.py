import re
from datetime import datetime
from typing import Optional, Dict


def parse_sms(text: str) -> Optional[Dict[str, str]]:
    """Parse bank SMS notification to extract amount and account."""
    amount_match = re.search(r"(\d+[.,]\d{2})", text)
    account_match = re.search(r"(\d{4,})", text)
    if not amount_match:
        return None
    amount = float(amount_match.group(1).replace(',', ''))
    account = account_match.group(1) if account_match else None
    return {
        "amount": amount,
        "account": account,
        "text": text,
        "time": datetime.utcnow(),
    }
