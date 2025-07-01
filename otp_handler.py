from flask import Blueprint, render_template, request, session, redirect, flash
from models import db, OTPEntry
from datetime import datetime, timedelta
import random
import string

otp_bp = Blueprint('otp', __name__)

def generate_otp(length: int = 6) -> str:
    """Return a numeric OTP code of given length."""
    return ''.join(random.choices(string.digits, k=length))


@otp_bp.route('/send-otp', methods=['POST'])
def send_otp():
    phone = request.form['phone']
    otp_code = generate_otp()

    entry = OTPEntry(phone=phone, otp_code=otp_code, created_at=datetime.utcnow())
    db.session.add(entry)
    db.session.commit()

    # In production this would send via SMS gateway
    print(f"[DEBUG] \u0e2a\u0e48\u0e07 OTP \u0e44\u0e1b\u0e17\u0e35 {phone} \u0e23\u0e2b\u0e31\u0e2a: {otp_code}")
    return render_template('otp_form.html', phone=phone)


@otp_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    phone = request.form['phone']
    otp_code = request.form['otp_code']

    entry = (
        OTPEntry.query.filter_by(phone=phone)
        .order_by(OTPEntry.created_at.desc())
        .first()
    )
    if entry and entry.otp_code == otp_code and datetime.utcnow() - entry.created_at < timedelta(minutes=5):
        session['otp_verified'] = True
        flash("\u0e22\u0e37\u0e19\u0e22\u0e31\u0e19 OTP \u0e2a\u0e33\u0e40\u0e23\u0e47\u0e08", "success")
        return redirect('/dashboard')
    flash("OTP \u0e44\u0e21\u0e48\u0e16\u0e39\u0e01\u0e15\u0e49\u0e2d\u0e07\u0e2b\u0e23\u0e37\u0e2d\u0e2b\u0e21\u0e14\u0e2d\u0e32\u0e22", "danger")
    return render_template('otp_form.html', phone=phone)
