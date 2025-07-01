"""Utilities for sending messages to LINE group."""
import os
import requests

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")


def push_message_to_line(text: str) -> None:
    """Send a push message to the configured LINE group."""
    if not (LINE_ACCESS_TOKEN and LINE_GROUP_ID):
        return
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_GROUP_ID,
        "messages": [{"type": "text", "text": text}],
    }
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        pass


def reply_message(reply_token: str, text: str) -> None:
    """Reply to a LINE message."""
    if not LINE_ACCESS_TOKEN:
        return
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers=headers,
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        pass


def link_user_account(db, User, Wallet, token: str, line_user_id: str) -> str:
    """Link a LINE user with a web account using verification token."""
    user = db.session.query(User).filter_by(verify_token=token).first()
    if not user:
        return "ไม่พบโทเคน"
    if db.session.query(User).filter(User.line_user_id == line_user_id, User.id != user.id).first():
        return "LINE นี้ถูกใช้แล้ว"
    user.line_user_id = line_user_id
    user.is_linked = True
    user.verify_token = None
    line_wallet = db.session.query(Wallet).filter_by(owner_id=line_user_id).first()
    user_wallet = db.session.query(Wallet).filter_by(owner_id=str(user.id)).first()
    if line_wallet:
        if user_wallet:
            user_wallet.balance += line_wallet.balance
            db.session.delete(line_wallet)
        else:
            line_wallet.owner_id = str(user.id)
            line_wallet.channel = "shared"
    elif user_wallet:
        user_wallet.channel = "shared"
    else:
        db.session.add(Wallet(owner_id=str(user.id), balance=0, channel="shared"))
    db.session.commit()
    return "เชื่อมบัญชีเรียบร้อย"
