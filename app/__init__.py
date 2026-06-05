import os
from flask import Flask
from app.config import config_by_name
from app.extensions import db, login_manager, socketio, mail, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    # Ensure upload directories exist
    for folder in ['uploads', 'qrcodes']:
        path = os.path.join(app.static_folder, folder)
        os.makedirs(path, exist_ok=True)

    # Register blueprints
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.user import user_bp
    from app.staff import staff_bp
    from app.reports import reports_bp
    from app.queue_ws import queue_ws

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(queue_ws)

    # Main routes
    from app.main_routes import main_bp
    app.register_blueprint(main_bp)

    # User loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

    # Template filters and globals
    @app.template_filter('datetime_format')
    def datetime_format(value, format='%b %d, %Y %I:%M %p'):
        if value is None:
            return ""
        return value.strftime(format)

    @app.template_filter('time_format')
    def time_format(value):
        if value is None:
            return ""
        return value.strftime('%I:%M %p')

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import Organization, Notification
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
        return dict(unread_notifications=unread_count)

    return app
