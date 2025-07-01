# -*- coding: utf-8 -*-
"""Flask app integrating web dashboard and LINE bot for betting."""
from __future__ import annotations

import os
import re
import uuid
import random
import base64
from io import BytesIO
from typing import Optional, Dict
from datetime import datetime, timedelta
import pytz

from dotenv import load_dotenv
from flask import (
    Flask,
    Blueprint,
    request,
    jsonify,
    render_template,
    abort,
    redirect,
    url_for,
    session,
)
from models import (
    db,
    User,
    Wallet,
    Round,
    Bet,
    Deposit,
    Withdrawal,
    Stream,
    DepositRequest,
    BetEntry,
    LogEntry,
    BetLog,
    WalletLog,
    SystemLog,
    SecurityLog,
    DepositPending,
    DepositLog,
    DepositNotification,
    AdminIntegrationSetting,
    DepositWebhookLog,
)
from socketio_app import socketio
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import bcrypt
import qrcode
from werkzeug.utils import secure_filename

from utils.line_helper import push_message_to_line, reply_message, link_user_account
from line_helper import get_line_login_url, get_line_profile
from sms_parser import parse_sms
from auto_matcher import match_deposit
from wallet import credit_wallet
from models import RegisteredBankAccount

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_USER = os.getenv("MYSQL_USER")
DB_PASS = os.getenv("MYSQL_PASS")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_NAME = os.getenv("MYSQL_DB")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
STREAM_URL = os.getenv("STREAM_URL", "")
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
UPLOAD_FOLDER = os.path.join("static", "uploads")
BET_ALERT = float(os.getenv("BET_ALERT", "10000"))
PROMPTPAY_ID = os.getenv("PROMPTPAY_ID")
LOGO_TEXT = os.getenv("LOGO_TEXT", "NN888")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}" if DB_USER else ""
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")

login_manager = LoginManager(app)
login_manager.login_view = "login"

db.init_app(app)


@app.context_processor
def inject_logo_text():
    """Provide logo text to all templates."""
    return {"logo_text": LOGO_TEXT}



# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def get_open_round() -> Optional[Round]:
    """Return the currently open round if any."""
    return Round.query.filter_by(status="open").order_by(Round.id.desc()).first()


def bet_totals(round_id: int) -> Dict[str, float]:
    """Return total bet amounts for the given round."""
    red = (
        db.session.query(db.func.coalesce(db.func.sum(Bet.amount), 0))
        .filter_by(round_id=round_id, side="red")
        .scalar()
    )
    blue = (
        db.session.query(db.func.coalesce(db.func.sum(Bet.amount), 0))
        .filter_by(round_id=round_id, side="blue")
        .scalar()
    )
    return {"red": float(red), "blue": float(blue)}


def current_stream_url() -> str:
    """Return HLS stream URL from DB or env."""
    stream = Stream.query.order_by(Stream.id.desc()).first()
    return stream.hls_url if stream else STREAM_URL


def log_system(action: str, detail: str = "") -> None:
    ip = request.remote_addr
    agent = request.headers.get("User-Agent")
    log = SystemLog(
        admin_id=str(current_user.id) if current_user.is_authenticated else None,
        action_type=action,
        detail=detail,
        ip_address=ip,
        user_agent=agent,
    )
    db.session.add(log)
    db.session.commit()


def log_security(event: str, severity: str, detail: str = "", user_id: Optional[str] = None) -> None:
    ip = request.remote_addr
    log = SecurityLog(
        user_id=user_id,
        event_type=event,
        severity=severity,
        detail=detail,
        ip_address=ip,
    )
    db.session.add(log)
    db.session.commit()


def get_wallet(owner_id: str, channel: str = "web") -> Wallet:
    wallet = Wallet.query.filter_by(owner_id=owner_id).first()
    if not wallet:
        wallet = Wallet(owner_id=owner_id, balance=0, channel=channel)
        db.session.add(wallet)
        db.session.commit()
    return wallet

# ---------------------------------------------------------------------------
# Deposit matching helpers
# ---------------------------------------------------------------------------

def match_deposit_sms(msg: str):
    """Match SMS text to a pending deposit by amount."""
    m = re.search(r"([0-9,]+\.[0-9]{2})", msg or "")
    if m:
        amount = float(m.group(1).replace(",", ""))
        dp = DepositPending.query.filter_by(amount=amount, status="pending").first()
        if dp:
            dp.status = "matched"
            db.session.commit()
            return {"user_id": dp.user_id, "amount": amount}
    return None


def update_wallet(user_id: int, amount: float):
    wallet = Wallet.query.filter_by(owner_id=str(user_id)).first()
    if wallet:
        wallet.balance += amount
        db.session.commit()
    return wallet


def log_deposit(user_id: int, amount: float, msg: str):
    log = DepositLog(user_id=user_id, amount=amount, message=msg)
    db.session.add(log)
    db.session.commit()


def admin_required(func):
    """Basic token auth decorator for admin endpoints."""

    def wrapper(*args, **kwargs):
        if ADMIN_TOKEN and request.headers.get("Authorization") != f"Bearer {ADMIN_TOKEN}":
            return abort(401)
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# User-facing Blueprints
# ---------------------------------------------------------------------------
user_bp = Blueprint("user_api", __name__, url_prefix="/api")
admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@user_bp.route("/bet", methods=["POST"])
@login_required
def place_bet():
    data = request.get_json(silent=True) or {}
    side = data.get("side")
    amount = float(data.get("amount", 0))
    if side not in {"red", "blue"} or amount < 10:
        db.session.add(BetLog(user_id=str(current_user.id), round_id=None, side=None, amount=amount, platform="web", status="failed"))
        db.session.commit()
        return jsonify({"error": "invalid data"}), 400
    rnd = get_open_round()
    if not rnd:
        db.session.add(BetLog(user_id=str(current_user.id), round_id=None, side=side, amount=amount, platform="web", status="rejected"))
        db.session.commit()
        return jsonify({"error": "no open round"}), 400
    wallet = get_wallet(str(current_user.id))
    if wallet.balance < amount:
        db.session.add(BetLog(user_id=str(current_user.id), round_id=rnd.id if rnd else None, side=side, amount=amount, platform="web", status="failed"))
        db.session.commit()
        return jsonify({"error": "balance"}), 400
    wallet.balance -= amount
    bet = Bet(user_id=current_user.id, round_id=rnd.id, side=side, amount=amount)
    db.session.add(bet)
    db.session.add(BetLog(user_id=str(current_user.id), round_id=rnd.id, side=side, amount=amount, platform="web", status="success"))
    db.session.commit()
    if amount >= BET_ALERT:
        push_message_to_line(f"ALERT: {current_user.username} bet {amount}")
    totals = bet_totals(rnd.id)
    socketio.emit(
        "new_bet",
        {
            "user_id": current_user.username,
            "side": side,
            "amount": amount,
            "totals": totals,
        },
        broadcast=True,
    )
    socketio.emit(
        "wallet_update",
        {"user_id": current_user.id, "balance": float(wallet.balance)},
        broadcast=True,
    )
    push_message_to_line(f"{current_user.username} เดิมพัน {side} {amount}")
    return jsonify({"status": "ok"})


@user_bp.route("/generate_qr/<int:amount>")
@login_required
def generate_qr(amount: int):
    """Generate PromptPay QR code with unique decimal."""
    if not PROMPTPAY_ID or amount <= 0:
        return jsonify({"error": "config"}), 400
    decimal_part = round(random.uniform(0.01, 0.99), 2)
    full_amount = round(amount + decimal_part, 2)
    ref = uuid.uuid4().hex[:8]
    expires = datetime.utcnow() + timedelta(minutes=15)
    req = DepositRequest(
        user_id=current_user.id,
        amount=amount,
        decimal=decimal_part,
        full_amount=full_amount,
        ref=ref,
        expires_at=expires,
    )
    db.session.add(req)
    db.session.commit()
    qr_content = f"promptpay://{PROMPTPAY_ID}?amount={full_amount:.2f}&ref={ref}"
    img = qrcode.make(qr_content)
    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return jsonify({
        "qr": f"data:image/png;base64,{qr_b64}",
        "amount": full_amount,
        "ref": ref,
        "expires": expires.isoformat(),
    })


@user_bp.route("/wallet/deposit_request", methods=["POST"])
@login_required
def deposit_request():
    amount = float(request.form.get("amount", 0))
    slip = request.files.get("slip")
    if amount <= 0 or not slip:
        db.session.add(WalletLog(user_id=str(current_user.id), action="deposit", amount=amount, status="failed", platform="web"))
        db.session.commit()
        return jsonify({"error": "data"}), 400
    fname = secure_filename(f"{uuid.uuid4().hex}_{slip.filename}")
    path = os.path.join(UPLOAD_FOLDER, fname)
    slip.save(path)
    dep = Deposit(user_id=current_user.id, amount=amount, slip_path=fname)
    db.session.add(dep)
    db.session.add(WalletLog(user_id=str(current_user.id), action="deposit", amount=amount, status="pending", platform="web", slip_url=fname))
    db.session.commit()
    return jsonify({"status": "pending"})


@user_bp.route("/wallet/withdraw_request", methods=["POST"])
@login_required
def withdraw_request():
    data = request.get_json(silent=True) or {}
    amount = float(data.get("amount", 0))
    bank = data.get("bank")
    account = data.get("account")
    name = data.get("name")
    if amount <= 0:
        db.session.add(WalletLog(user_id=str(current_user.id), action="withdraw", amount=amount, status="failed", platform="web"))
        db.session.commit()
        return jsonify({"error": "data"}), 400
    if not bank or not account:
        reg = RegisteredBankAccount.query.filter_by(user_id=current_user.id).first()
        if reg:
            bank = reg.bank_name
            account = reg.account_number
            name = reg.account_name
        else:
            db.session.add(WalletLog(user_id=str(current_user.id), action="withdraw", amount=amount, status="failed", platform="web"))
            db.session.commit()
            return jsonify({"error": "bank"}), 400
    wallet = get_wallet(str(current_user.id))
    if wallet.balance < amount:
        db.session.add(WalletLog(user_id=str(current_user.id), action="withdraw", amount=amount, status="failed", platform="web"))
        db.session.commit()
        return jsonify({"error": "balance"}), 400
    wallet.balance -= amount
    wd = Withdrawal(
        user_id=current_user.id,
        amount=amount,
        bank_name=bank,
        bank_account=account,
    )
    db.session.add(wd)
    db.session.add(WalletLog(user_id=str(current_user.id), action="withdraw", amount=amount, status="pending", platform="web"))
    db.session.commit()
    socketio.emit(
        "wallet_update",
        {"user_id": current_user.id, "balance": float(wallet.balance)},
        broadcast=True,
    )
    return jsonify({"status": "pending", "balance": float(wallet.balance)})


@user_bp.route("/link_token", methods=["POST"])
@login_required
def link_token():
    token = uuid.uuid4().hex[:6]
    current_user.verify_token = token
    db.session.commit()
    return jsonify({"token": token})


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
@admin_bp.route("/open_round", methods=["POST"])
@admin_required
def open_round():
    data = request.get_json(silent=True) or {}
    red = data.get("red_odds")
    blue = data.get("blue_odds")
    if red is None or blue is None:
        return jsonify({"error": "missing odds"}), 400
    Round.query.filter_by(status="open").update({"status": "closed"})
    rnd = Round(status="open", red_odds=red, blue_odds=blue)
    db.session.add(rnd)
    db.session.add(SystemLog(admin_id=str(current_user.id), action_type="open_round", detail=f"{red}/{blue}", ip_address=request.remote_addr, user_agent=request.headers.get("User-Agent")))
    db.session.commit()
    socketio.emit(
        "round_open",
        {"red_odds": float(red), "blue_odds": float(blue), "totals": {"red": 0, "blue": 0}},
        broadcast=True,
    )
    socketio.emit("totals", {"red": 0, "blue": 0}, broadcast=True)
    push_message_to_line(f"เปิดรอบ ราคา {red}/{blue}")
    return jsonify({"status": "ok"})


@admin_bp.route("/close_round", methods=["POST"])
@admin_required
def close_round():
    rnd = get_open_round()
    if not rnd:
        return jsonify({"error": "no open round"}), 400
    rnd.status = "closed"
    db.session.add(SystemLog(admin_id=str(current_user.id), action_type="close_round", detail=str(rnd.id), ip_address=request.remote_addr, user_agent=request.headers.get("User-Agent")))
    db.session.commit()
    socketio.emit("round_close", broadcast=True)
    push_message_to_line("ปิดรอบ")
    return jsonify({"status": "ok"})


@admin_bp.route("/result", methods=["POST"])
@admin_required
def result():
    data = request.get_json(silent=True) or {}
    winner = data.get("winner")
    if winner not in {"red", "blue"}:
        return jsonify({"error": "invalid winner"}), 400
    rnd = Round.query.filter_by(status="closed").order_by(Round.id.desc()).first()
    if not rnd:
        return jsonify({"error": "no closed round"}), 400
    rnd.status = "settled"
    rnd.result = winner
    db.session.add(SystemLog(admin_id=str(current_user.id), action_type="result_declared", detail=f"{rnd.id}:{winner}", ip_address=request.remote_addr, user_agent=request.headers.get("User-Agent")))
    db.session.commit()
    socketio.emit("result_announced", {"winner": winner}, broadcast=True)
    push_message_to_line(f"ผล {winner} ชนะ")
    return jsonify({"status": "ok"})


@admin_bp.route("/deposits", methods=["GET"])
@admin_required
def list_deposits():
    deps = Deposit.query.filter_by(status="pending").all()
    data = [
        {"id": d.id, "user": d.user_id, "amount": float(d.amount), "slip": d.slip_path}
        for d in deps
    ]
    return jsonify(data)


@admin_bp.route("/deposits/<int:dep_id>/approve", methods=["POST"])
@admin_required
def approve_deposit(dep_id: int):
    dep = Deposit.query.get_or_404(dep_id)
    if dep.status != "pending":
        return jsonify({"error": "done"}), 400
    dep.status = "approved"
    wallet = credit_wallet(dep.user_id, float(dep.amount), source="admin")
    log_system("approve_deposit", f"{dep.user_id} {dep.amount}")
    db.session.commit()
    socketio.emit(
        "wallet_update",
        {"user_id": dep.user_id, "balance": float(wallet.balance)},
        broadcast=True,
    )
    push_message_to_line(f"อนุมัติฝากเงินผู้ใช้ {dep.user_id} จำนวน {float(dep.amount)}")
    return jsonify({"status": "ok"})


@admin_bp.route("/deposits/<int:dep_id>/reject", methods=["POST"])
@admin_required
def reject_deposit(dep_id: int):
    dep = Deposit.query.get_or_404(dep_id)
    if dep.status != "pending":
        return jsonify({"error": "done"}), 400
    dep.status = "rejected"
    db.session.add(WalletLog(user_id=str(dep.user_id), action="deposit", amount=dep.amount,
                             status="rejected", platform="admin", slip_url=dep.slip_path))
    log_system("reject_deposit", f"{dep.user_id} {dep.amount}")
    db.session.commit()
    push_message_to_line(f"ปฏิเสธการฝากเงินผู้ใช้ {dep.user_id} จำนวน {float(dep.amount)}")
    return jsonify({"status": "ok"})


@admin_bp.route("/withdrawals", methods=["GET"])
@admin_required
def list_withdrawals():
    wds = Withdrawal.query.filter_by(status="pending").all()
    data = [
        {
            "id": w.id,
            "user": w.user_id,
            "amount": float(w.amount),
            "bank": w.bank_name,
            "account": w.bank_account,
        }
        for w in wds
    ]
    return jsonify(data)


@admin_bp.route("/withdrawals/<int:wd_id>/approve", methods=["POST"])
@admin_required
def approve_withdrawal(wd_id: int):
    wd = Withdrawal.query.get_or_404(wd_id)
    if wd.status != "pending":
        return jsonify({"error": "done"}), 400
    wd.status = "approved"
    db.session.add(WalletLog(user_id=str(wd.user_id), action="withdraw", amount=wd.amount, status="success", platform="admin"))
    log_system("approve_withdrawal", f"{wd.user_id} {wd.amount}")
    db.session.commit()
    push_message_to_line(f"อนุมัติถอนเงินผู้ใช้ {wd.user_id} จำนวน {float(wd.amount)}")
    return jsonify({"status": "ok"})


@admin_bp.route("/withdrawals/<int:wd_id>/reject", methods=["POST"])
@admin_required
def reject_withdrawal(wd_id: int):
    wd = Withdrawal.query.get_or_404(wd_id)
    if wd.status != "pending":
        return jsonify({"error": "done"}), 400
    wd.status = "rejected"
    wallet = get_wallet(str(wd.user_id))
    wallet.balance += wd.amount
    db.session.add(WalletLog(user_id=str(wd.user_id), action="withdraw", amount=wd.amount,
                             status="rejected", platform="admin"))
    log_system("reject_withdrawal", f"{wd.user_id} {wd.amount}")
    db.session.commit()
    socketio.emit(
        "wallet_update",
        {"user_id": wd.user_id, "balance": float(wallet.balance)},
        broadcast=True,
    )
    push_message_to_line(f"ปฏิเสธการถอนเงินผู้ใช้ {wd.user_id} จำนวน {float(wd.amount)}")
    return jsonify({"status": "ok"})


@admin_bp.route("/deposit_requests", methods=["GET"])
@admin_required
def list_deposit_requests():
    reqs = DepositRequest.query.order_by(DepositRequest.id.desc()).all()
    data = [
        {
            "id": r.id,
            "user": r.user_id,
            "amount": float(r.full_amount),
            "status": r.status,
            "expires": r.expires_at.isoformat() if r.expires_at else None,
        }
        for r in reqs
    ]
    return jsonify(data)


@admin_bp.route("/deposit_requests/<int:req_id>/confirm", methods=["POST"])
@admin_required
def confirm_deposit_request(req_id: int):
    req = DepositRequest.query.get_or_404(req_id)
    if req.status != "pending":
        return jsonify({"error": "done"}), 400
    req.status = "matched"
    wallet = credit_wallet(req.user_id, float(req.full_amount), source="admin")
    socketio.emit(
        "wallet_update",
        {"user_id": req.user_id, "balance": float(wallet.balance)},
        broadcast=True,
    )
    push_message_to_line(
        f"ยืนยันยอดฝาก {req.full_amount:.2f} ของผู้ใช้ {req.user_id}"
    )
    return jsonify({"status": "ok"})


@admin_bp.route("/sms", methods=["POST"])
@admin_required
def sms_webhook():
    text = request.form.get("text") or request.json.get("text")
    if not text:
        return jsonify({"error": "no text"}), 400
    info = parse_sms(text)
    if not info:
        return jsonify({"error": "parse"}), 400
    matched = match_deposit(info["amount"], info.get("account"))
    return jsonify({"matched": matched})


@app.route('/api/sms-webhook', methods=['POST'])
def api_sms_webhook():
    sms_body = request.form.get('message') or (request.json or {}).get('message')
    matched = match_deposit_sms(sms_body)
    if matched:
        update_wallet(matched['user_id'], matched['amount'])
        log_deposit(matched['user_id'], matched['amount'], sms_body)
        socketio.emit('deposit_update', matched, broadcast=True)
    return jsonify({'status': 'ok'})


@app.route('/api/ifttt-webhook', methods=['POST'])
def ifttt_webhook():
    data = request.json or request.form
    msg = data.get('value1')
    matched = match_deposit_sms(msg)
    if matched:
        update_wallet(matched['user_id'], matched['amount'])
        log_deposit(matched['user_id'], matched['amount'], msg)
        socketio.emit('deposit_update', matched, broadcast=True)
    return jsonify({'status': 'ok'})


@app.route('/api/pushbullet-webhook', methods=['POST'])
def pushbullet_webhook():
    data = request.json or request.form
    body = data.get('push', {}).get('body') if 'push' in data else data.get('body')
    matched = match_deposit_sms(body)
    if matched:
        update_wallet(matched['user_id'], matched['amount'])
        log_deposit(matched['user_id'], matched['amount'], body)
        socketio.emit('deposit_update', matched, broadcast=True)
    return jsonify({'status': 'ok'})


@app.route('/api/line-webhook', methods=['POST'])
def line_deposit_webhook():
    data = request.json or {}
    msg = data.get('events', [{}])[0].get('message', {}).get('text')
    matched = match_deposit_sms(msg)
    if matched:
        update_wallet(matched['user_id'], matched['amount'])
        log_deposit(matched['user_id'], matched['amount'], msg)
        socketio.emit('deposit_update', matched, broadcast=True)
    return jsonify({'status': 'ok'})


@admin_bp.route("/stream", methods=["POST"])
@admin_required
def update_stream():
    url = request.get_json().get("hls_url")
    if not url:
        return jsonify({"error": "url"}), 400
    stream = Stream(hls_url=url)
    db.session.add(stream)
    db.session.add(SystemLog(admin_id=str(current_user.id) if current_user.is_authenticated else None,
                              action_type="update_stream", detail=url,
                              ip_address=request.remote_addr,
                              user_agent=request.headers.get("User-Agent")))
    db.session.commit()
    socketio.emit("stream_update", {"url": url}, broadcast=True)
    return jsonify({"status": "ok"})


@admin_bp.route("/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.id.asc()).all()
    balances = {u.id: float(get_wallet(str(u.id)).balance) for u in users}
    return render_template("admin_users.html", users=users, balances=balances)


@admin_bp.route("/users/<int:uid>", methods=["GET", "POST"])
@admin_required
def admin_user_detail(uid: int):
    user = User.query.get_or_404(uid)
    if request.method == "POST":
        phone = request.form.get("phone")
        line_id = request.form.get("line_user_id")
        if phone and phone != user.phone:
            if User.query.filter_by(phone=phone).first():
                return "duplicate phone", 400
            user.phone = phone
        if line_id and line_id != user.line_user_id:
            if User.query.filter_by(line_user_id=line_id).first():
                return "duplicate line", 400
            user.line_user_id = line_id
        user.is_linked = bool(user.line_user_id)
        db.session.add(user)
        log_system("edit_user", f"{user.id}")
        db.session.commit()
        return redirect(url_for("admin_api.admin_user_detail", uid=uid))
    wallet = get_wallet(str(user.id))
    return render_template("admin_user_detail.html", user=user, wallet=wallet)


@admin_bp.route("/bets/<int:user_id>")
@admin_required
def admin_bets_user(user_id: int):
    user = User.query.get_or_404(user_id)
    bets = Bet.query.filter_by(user_id=user.id).order_by(Bet.id.desc()).all()
    return render_template("admin_bets_user.html", bets=bets, user=user)


@admin_bp.route("/bets/round/<int:round_id>")
@admin_required
def admin_bets_round(round_id: int):
    rnd = Round.query.get_or_404(round_id)
    bets = Bet.query.filter_by(round_id=rnd.id).order_by(Bet.id.desc()).all()
    return render_template("admin_bets_round.html", bets=bets, rnd=rnd)


@admin_bp.route("/deposit_logs")
@admin_required
def admin_deposit_logs():
    """View deposit logs for all users."""
    logs = DepositLog.query.order_by(DepositLog.created_at.desc()).limit(100).all()
    return render_template("admin_deposit_logs.html", logs=logs)


@admin_bp.route("/deposit_notifications")
@admin_required
def admin_deposit_notifications():
    notifications = DepositNotification.query.order_by(DepositNotification.received_at.desc()).limit(100).all()
    return render_template("admin_notifications.html", notifications=notifications)


@app.route('/admin/deposit/force_match', methods=['POST'])
@login_required
def admin_force_match():
    if not current_user.is_admin:
        return "Forbidden", 403
    dep_id = request.form.get('deposit_id')
    dep = DepositPending.query.get(dep_id)
    if not dep or dep.status != 'pending':
        return "Deposit not found or already processed"
    wallet = Wallet.query.filter_by(owner_id=dep.user_id).first()
    wallet.balance += dep.amount
    dep.status = 'force_matched'
    db.session.add(wallet)
    db.session.add(dep)
    db.session.add(DepositLog(user_id=dep.user_id, amount=dep.amount, message='Force matched by admin'))
    db.session.commit()
    socketio.emit('deposit_force_matched', {'user_id': dep.user_id, 'amount': dep.amount}, namespace='/admin', broadcast=True)
    return redirect('/admin/deposit/logs')


@app.route('/admin/deposit/mark_fraud', methods=['POST'])
@login_required
def admin_mark_fraud():
    if not current_user.is_admin:
        return "Forbidden", 403
    dep_id = request.form.get('deposit_id')
    dep = DepositPending.query.get(dep_id)
    if not dep or dep.status != 'pending':
        return "Deposit not found or already processed"
    dep.status = 'fraud'
    db.session.add(dep)
    db.session.add(DepositLog(user_id=dep.user_id, amount=dep.amount, message='Marked as fraud'))
    db.session.commit()
    socketio.emit('deposit_marked_fraud', {'user_id': dep.user_id, 'amount': dep.amount}, namespace='/admin', broadcast=True)
    return redirect('/admin/deposit/logs')


@app.route('/admin/setup-forwarder', methods=['GET', 'POST'])
def admin_setup_forwarder():
    if request.method == 'POST':
        session['forwarder_method'] = request.form.get('method')
        session['sms_phone'] = request.form.get('sms_phone')
        session['ifttt_key'] = request.form.get('ifttt_key')
        session['push_token'] = request.form.get('push_token')
        return "บันทึกเรียบร้อย"
    return render_template('admin_forwarder_settings.html')


# ---------------------------------------------------------------------------
# LINE webhook
# ---------------------------------------------------------------------------
@app.route("/callback", methods=["POST"])
def line_webhook():
    body = request.get_json(force=True)
    events = body.get("events", [])
    for ev in events:
        if ev.get("type") != "message" or ev["message"].get("type") != "text":
            continue
        reply_token = ev.get("replyToken")
        line_uid = ev["source"].get("userId")
        text = ev["message"].get("text", "").strip()
        if text.lower().startswith("link "):
            token = text.split(" ", 1)[1]
            msg = link_user_account(db, User, Wallet, token, line_uid)
            reply_message(reply_token, msg)
            continue
        if re.match(r"^(แดง|น้ำเงิน)\s+\d+", text):
            side_txt, amt = text.split()[:2]
            side = "red" if side_txt.startswith("แดง") else "blue"
            amount = float(amt)
            if amount < 10:
                reply_message(reply_token, "ยอดต่ำสุด 10")
                continue
            rnd = get_open_round()
            if not rnd:
                reply_message(reply_token, "ยังไม่เปิดรอบ")
                continue
            user = User.query.filter_by(line_user_id=line_uid).first()
            owner_id = str(user.id) if user else line_uid
            wallet = get_wallet(owner_id, "shared" if user else "line")
            if wallet.balance < amount:
                reply_message(reply_token, "ยอดเงินไม่พอ")
                db.session.add(BetLog(user_id=owner_id, round_id=rnd.id if rnd else None, side=side, amount=amount, platform="line", status="failed"))
                db.session.commit()
                continue
            wallet.balance -= amount
            bet = Bet(user_id=user.id if user else None, round_id=rnd.id, side=side, amount=amount)
            db.session.add(bet)
            db.session.add(BetLog(user_id=owner_id, round_id=rnd.id, side=side, amount=amount, platform="line", status="success"))
            db.session.commit()
            if amount >= BET_ALERT:
                push_message_to_line(f"ALERT: {owner_id} bet {amount}")
            totals = bet_totals(rnd.id)
            socketio.emit(
                "new_bet",
                {
                    "user_id": user.username if user else line_uid,
                    "side": side,
                    "amount": amount,
                    "totals": totals,
                },
                broadcast=True,
            )
            socketio.emit(
                "wallet_update",
                {"user_id": user.id if user else line_uid, "balance": float(wallet.balance)},
                broadcast=True,
            )
            reply_message(reply_token, "บันทึกการเดิมพันแล้ว")
            continue
        if text.lower() in {"c", "cc"}:
            user = User.query.filter_by(line_user_id=line_uid).first()
            owner_id = str(user.id) if user else line_uid
            wallet = get_wallet(owner_id)
            bets = Bet.query.join(Round).filter(Round.status == "open", Bet.user_id == (user.id if user else None)).all()
            total = sum(float(b.amount) for b in bets)
            link_msg = f"\nเปิดเว็บ: /dashboard" if user else "\nพิมพ์ link <token> ในเว็บเพื่อเชื่อม"  # placeholder
            reply_message(reply_token, f"ยอดคงเหลือ {wallet.balance}\nยอดเดิมพัน {total}{link_msg}")
# Add a simple OK response for LINE Messaging API webhook
    return "OK"


# ---------------------------------------------------------------------------
# LINE Login routes
# ---------------------------------------------------------------------------

@app.route("/line-login")
def line_login():
    return redirect(get_line_login_url())


@app.route("/callback", methods=["GET"])
def line_callback():
    code = request.args.get("code")
    profile = get_line_profile(code) if code else None
    if profile:
        user = User.query.filter_by(line_user_id=profile["line_user_id"]).first()
        if user:
            login_user(user)
            return redirect("/dashboard")
        return "ยังไม่มีบัญชีที่ผูกกับ LINE นี้"
    return "เกิดข้อผิดพลาดในการเข้าสู่ระบบ"


# ---------------------------------------------------------------------------
# Auth routes and pages
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        phone = request.form.get("phone")
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="ชื่อผู้ใช้นี้มีอยู่แล้ว")
        if phone and User.query.filter_by(phone=phone).first():
            return render_template("register.html", error="เบอร์นี้ถูกใช้แล้ว")
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(username=username, password_hash=pw_hash, phone=phone, registered_ip=request.remote_addr)
        db.session.add(user)
        db.session.commit()
        get_wallet(str(user.id), "web")
        login_user(user)
        if not RegisteredBankAccount.query.filter_by(user_id=user.id).first():
            return redirect(url_for("bank_setup"))
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            log_security("login_failed", "medium", user_id=username)
            # check recent failures
            one_min_ago = datetime.utcnow() - timedelta(minutes=1)
            cnt = SecurityLog.query.filter_by(event_type="login_failed", ip_address=request.remote_addr).filter(SecurityLog.created_at >= one_min_ago).count()
            if cnt >= 5:
                push_message_to_line(f"ALERT: multiple failed logins from {request.remote_addr}")
            return render_template("login.html", error="ข้อมูลไม่ถูกต้อง")
        login_user(user)
        log_security("login_success", "low", user_id=str(user.id))
        if not RegisteredBankAccount.query.filter_by(user_id=user.id).first():
            return redirect(url_for("bank_setup"))
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    wallet = get_wallet(str(current_user.id))
    linked = current_user.line_user_id is not None
    bank = RegisteredBankAccount.query.filter_by(user_id=current_user.id).first()
    bets = (
        Bet.query.filter_by(user_id=current_user.id)
        .order_by(Bet.id.desc())
        .limit(5)
        .all()
    )
    return render_template("dashboard.html",
        stream_url=current_stream_url(),
        balance=float(wallet.balance),
        user=current_user,
        linked=linked,
        bets=bets,
        bank=bank,
    )


@app.route("/profile")
@login_required
def profile_page():
    wallet = get_wallet(str(current_user.id))
    bet_count = Bet.query.filter_by(user_id=current_user.id).count()
    return render_template("profile.html", user=current_user, wallet=wallet, bet_count=bet_count)


@app.route("/mybets")
@login_required
def mybets_page():
    bets = Bet.query.filter_by(user_id=current_user.id).order_by(Bet.id.desc()).all()
    return render_template("mybets.html", bets=bets)


@app.route("/wallet/history")
@login_required
def wallet_history_page():
    logs = WalletLog.query.filter_by(user_id=str(current_user.id)).order_by(WalletLog.id.desc()).all()
    return render_template("wallet_history.html", logs=logs)


@app.route('/bet')
@login_required
def bet_page():
    return render_template('bet.html')


@app.route('/history')
@login_required
def user_history():
    """Show bet and wallet logs for the current user."""
    bets = (
        Bet.query.filter_by(user_id=current_user.id)
        .order_by(Bet.created_at.desc())
        .all()
    )
    wallet_logs = (
        WalletLog.query.filter_by(user_id=current_user.id)
        .order_by(WalletLog.created_at.desc())
        .all()
    )
    return render_template('user_history.html', bets=bets, wallet_logs=wallet_logs)


@app.route('/stream')
@login_required
def stream_page():
    wallet = get_wallet(str(current_user.id))
    return render_template('stream.html', stream_url=current_stream_url(), wallet=wallet)


@app.route("/bank_setup", methods=["GET", "POST"])
@login_required
def bank_setup():
    """Initial bank account registration."""
    existing = RegisteredBankAccount.query.filter_by(user_id=current_user.id).first()
    if existing:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        bank_name = request.form.get("bank_name")
        account_number = request.form.get("account_number")
        account_name = request.form.get("account_name")
        if not (bank_name and account_number and account_name):
            return render_template("bank_setup.html", error="กรอกข้อมูลให้ครบ")
        acc = RegisteredBankAccount(
            user_id=current_user.id,
            bank_name=bank_name,
            account_number=account_number,
            account_name=account_name,
        )
        db.session.add(acc)
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("bank_setup.html")




@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit_page():
    """Display PromptPay QR for deposit."""
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            amount = 0
        if amount <= 0 or not PROMPTPAY_ID:
            return render_template("deposit.html", error="จำนวนไม่ถูกต้อง")
        decimal_part = round(random.uniform(0.01, 0.99), 2)
        full_amount = round(amount + decimal_part, 2)
        ref = uuid.uuid4().hex[:8]
        expires = datetime.utcnow() + timedelta(minutes=15)
        req = DepositRequest(
            user_id=current_user.id,
            amount=amount,
            decimal=decimal_part,
            full_amount=full_amount,
            ref=ref,
            expires_at=expires,
        )
        db.session.add(req)
        db.session.commit()
        qr_content = f"promptpay://{PROMPTPAY_ID}?amount={full_amount:.2f}&ref={ref}"
        img = qrcode.make(qr_content)
        buf = BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        return render_template(
            "deposit.html",
            qr=qr_b64,
            full_amount=f"{full_amount:.2f}",
            ref=ref,
        )
    return render_template("deposit.html")


@app.route('/deposit/history')
@login_required
def deposit_history():
    logs = DepositPending.query.filter_by(user_id=current_user.id).order_by(DepositPending.created_at.desc()).all()
    return render_template('deposit_history.html', logs=logs)

@app.route("/logs")
@login_required
def logs_page():
    return render_template("logs.html")


@app.route('/admin/logs')
@login_required
def admin_logs_page():
    if not current_user.is_admin:
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้"
    logs = LogEntry.query.order_by(LogEntry.timestamp.desc()).limit(100).all()
    return render_template('admin_logs.html', logs=logs)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "Forbidden", 403
    logs = DepositWebhookLog.query.order_by(DepositWebhookLog.created_at.desc()).limit(50).all()
    return render_template('admin_dashboard.html', logs=logs)


def notify_admin(msg: str) -> None:
    """Emit a simple notification message to all admin clients."""
    socketio.emit('admin_notify', {'msg': msg}, broadcast=True)


@app.route("/api/health")
def health_check():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return redirect(url_for("dashboard")) if current_user.is_authenticated else redirect(url_for("login"))


# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
from admin_logs import logs_bp
app.register_blueprint(logs_bp)


@socketio.on("connect")
def on_connect():
    if current_user.is_authenticated:
        from flask_socketio import join_room

        join_room(str(current_user.id))
    rnd = get_open_round()
    if rnd:
        emit_data = {
            "red_odds": float(rnd.red_odds),
            "blue_odds": float(rnd.blue_odds),
            "totals": bet_totals(rnd.id),
        }
        socketio.emit("round_open", emit_data)
        socketio.emit("totals", emit_data["totals"])


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
