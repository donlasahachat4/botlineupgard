from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import db, IntegrationConfig, IntegrationLog

integration_bp = Blueprint('integration_manager', __name__)

@integration_bp.route('/admin/integrations', methods=['GET', 'POST'])
@login_required
def manage_integrations():
    if request.method == 'POST':
        name = request.form['name']
        is_enabled = request.form.get('enable') == 'on'
        token = request.form.get('token', '')
        webhook_url = request.form.get('webhook_url', '')
        cfg = IntegrationConfig.query.filter_by(name=name).first()
        if not cfg:
            cfg = IntegrationConfig(name=name)
            db.session.add(cfg)
        cfg.is_enabled = is_enabled
        cfg.token = token
        cfg.webhook_url = webhook_url
        cfg.last_updated = datetime.utcnow()
        db.session.commit()

        log = IntegrationLog(
            integration=name,
            action='enable' if is_enabled else 'disable',
            detail=f'token:{token}, url:{webhook_url}',
            status='success',
            admin=current_user.username
        )
        db.session.add(log)
        db.session.commit()
    integrations = IntegrationConfig.query.all()
    return render_template('admin_integration.html', integrations=integrations)


@integration_bp.route('/admin/integration-logs')
@login_required
def integration_logs():
    logs = IntegrationLog.query.order_by(IntegrationLog.timestamp.desc()).limit(100).all()
    return render_template('admin_integration_logs.html', logs=logs)
