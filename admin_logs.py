from flask import Blueprint, request, jsonify, abort
from flask_login import login_required
from sqlalchemy import and_
from datetime import datetime
import pytz

from integrated_web import db, admin_required, BetLog, WalletLog, SystemLog, SecurityLog

logs_bp = Blueprint('logs_api', __name__, url_prefix='/api/logs')

TZ = pytz.timezone('Asia/Bangkok')


def parse_dates():
    start = request.args.get('start')
    end = request.args.get('end')
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None
    return start_dt, end_dt


@logs_bp.route('/bets')
@admin_required
def bet_logs():
    user_id = request.args.get('user_id')
    round_id = request.args.get('round_id')
    start, end = parse_dates()
    query = BetLog.query
    if user_id:
        query = query.filter(BetLog.user_id == user_id)
    if round_id:
        query = query.filter(BetLog.round_id == round_id)
    if start:
        query = query.filter(BetLog.created_at >= start)
    if end:
        query = query.filter(BetLog.created_at <= end)
    logs = query.order_by(BetLog.id.desc()).all()
    data = [
        {
            'id': l.id,
            'user_id': l.user_id,
            'round_id': l.round_id,
            'side': l.side,
            'amount': float(l.amount),
            'platform': l.platform,
            'status': l.status,
            'created_at': l.created_at.astimezone(TZ).strftime('%Y-%m-%d %H:%M')
        }
        for l in logs
    ]
    return jsonify(data)


@logs_bp.route('/wallets')
@admin_required
def wallet_logs():
    user_id = request.args.get('user_id')
    start, end = parse_dates()
    query = WalletLog.query
    if user_id:
        query = query.filter(WalletLog.user_id == user_id)
    if start:
        query = query.filter(WalletLog.created_at >= start)
    if end:
        query = query.filter(WalletLog.created_at <= end)
    logs = query.order_by(WalletLog.id.desc()).all()
    data = [
        {
            'id': l.id,
            'user_id': l.user_id,
            'action': l.action,
            'amount': float(l.amount),
            'status': l.status,
            'platform': l.platform,
            'slip_url': l.slip_url,
            'created_at': l.created_at.astimezone(TZ).strftime('%Y-%m-%d %H:%M')
        }
        for l in logs
    ]
    return jsonify(data)


@logs_bp.route('/system')
@admin_required
def system_logs():
    start, end = parse_dates()
    query = SystemLog.query
    if start:
        query = query.filter(SystemLog.created_at >= start)
    if end:
        query = query.filter(SystemLog.created_at <= end)
    logs = query.order_by(SystemLog.id.desc()).all()
    data = [
        {
            'id': l.id,
            'admin_id': l.admin_id,
            'action_type': l.action_type,
            'detail': l.detail,
            'ip_address': l.ip_address,
            'user_agent': l.user_agent,
            'created_at': l.created_at.astimezone(TZ).strftime('%Y-%m-%d %H:%M')
        }
        for l in logs
    ]
    return jsonify(data)


@logs_bp.route('/security')
@admin_required
def security_logs():
    user_id = request.args.get('user_id')
    start, end = parse_dates()
    query = SecurityLog.query
    if user_id:
        query = query.filter(SecurityLog.user_id == user_id)
    if start:
        query = query.filter(SecurityLog.created_at >= start)
    if end:
        query = query.filter(SecurityLog.created_at <= end)
    logs = query.order_by(SecurityLog.id.desc()).all()
    data = [
        {
            'id': l.id,
            'user_id': l.user_id,
            'event_type': l.event_type,
            'severity': l.severity,
            'detail': l.detail,
            'ip_address': l.ip_address,
            'created_at': l.created_at.astimezone(TZ).strftime('%Y-%m-%d %H:%M')
        }
        for l in logs
    ]
    return jsonify(data)

