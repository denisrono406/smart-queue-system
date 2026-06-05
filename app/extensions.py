from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
mail = Mail()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
