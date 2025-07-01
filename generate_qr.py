import os
import random
from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from pypromptpay import generate_payload
import segno
from models import db, DepositPending


generate_qr_bp = Blueprint('generate_qr', __name__)


@generate_qr_bp.route('/deposit/qr', methods=['GET', 'POST'])
@login_required
def deposit_qr():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except (TypeError, ValueError):
            amount = 0
        if amount <= 0:
            return render_template('deposit_qr_form.html', error='จำนวนไม่ถูกต้อง')

        amount_rand = round(int(amount) + random.uniform(0.01, 0.99), 2)
        dep = DepositPending(user_id=current_user.id, amount=amount_rand, status='pending', created_at=datetime.utcnow())
        db.session.add(dep)
        db.session.commit()

        pp_id = os.environ.get('PROMPTPAY_ID', '099XXXXXXXX')
        payload = generate_payload(pp_id, amount=amount_rand)
        qr_file = f'static/qr/{dep.id}.png'
        qr = segno.make(payload, error='M')
        qr.save(qr_file, scale=6)

        return render_template('deposit_qr_show.html', amount=amount_rand, qr_img=qr_file)
    return render_template('deposit_qr_form.html')
