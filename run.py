import os
from app import create_app
from app.extensions import db, socketio
from seed import seed

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=False, allow_unsafe_werkzeug=True)
