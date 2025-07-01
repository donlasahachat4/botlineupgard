from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, AdminIntegrationSetting

admin_integration_bp = Blueprint('admin_integration', __name__)

@admin_integration_bp.route('/admin/integration', methods=['GET', 'POST'])
@login_required
def integration():
    webhook_url = request.host_url.rstrip('/') + '/webhook/deposit'
    if request.method == 'POST':
        channel = request.form['channel']
        setting = AdminIntegrationSetting.query.first()
        if not setting:
            setting = AdminIntegrationSetting()
            db.session.add(setting)
        setting.channel = channel
        setting.ifttt_key = request.form.get('ifttt_key')
        setting.pushbullet_token = request.form.get('pushbullet_token')
        setting.line_channel_secret = request.form.get('line_channel_secret')
        setting.line_channel_access_token = request.form.get('line_channel_access_token')
        db.session.commit()
        flash('ตั้งค่าการเชื่อมต่อสำเร็จ')
        return redirect(url_for('admin_integration.integration'))
    return render_template('admin_integration.html', webhook_url=webhook_url)
