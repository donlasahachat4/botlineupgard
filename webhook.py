from flask import Blueprint, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import re
from models import db, Wallet, DepositWebhookLog, User, IntegrationLog
from datetime import datetime
from flask_socketio import emit
from auto_matcher import auto_matcher
from socketio_app import emit_balance_update, emit_admin_notify

webhook_bp = Blueprint('webhook', __name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@webhook_bp.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    return 'OK', 200


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="คุณพิมพ์ว่า: " + event.message.text)
    )


@webhook_bp.route('/webhook/deposit', methods=['POST'])
def deposit_webhook():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    channel = request.headers.get('X-Integration-Channel') or request.args.get('channel', 'webhook')
    matched, user, amount = auto_matcher(payload)
    status = 'auto-matched' if matched else 'pending'

    log = IntegrationLog(
        integration=channel,
        action='webhook',
        detail=str(payload),
        status=status,
        admin='system',
        timestamp=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()

    if matched and user and amount:
        wallet = Wallet.query.filter_by(owner_id=user.id).first()
        if wallet:
            wallet.balance += amount
            db.session.commit()
            emit_balance_update(user.id, float(wallet.balance))
            emit_admin_notify({'type': 'deposit', 'user': user.username, 'amount': amount})

    return jsonify({'status': status})
