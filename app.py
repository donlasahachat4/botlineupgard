import os
from integrated_web import app, socketio
from otp_handler import otp_bp
from webhook import webhook_bp
from admin_integration import admin_integration_bp
from integration_manager import integration_bp
from generate_qr import generate_qr_bp
import socketio_app  # registers Socket.IO events

app.register_blueprint(otp_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(generate_qr_bp)
app.register_blueprint(admin_integration_bp)
app.register_blueprint(integration_bp)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 8000)), debug=True)
