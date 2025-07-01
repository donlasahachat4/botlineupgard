import os
from integrated_web import app, socketio

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 8000)))
