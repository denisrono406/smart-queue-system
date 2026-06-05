import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Supabase PostgreSQL connection
    SUPABASE_URL = os.environ.get('VITE_SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('VITE_SUPABASE_ANON_KEY', '')

    # For SQLAlchemy direct connection, construct from Supabase URL
    _supabase_host = SUPABASE_URL.replace('https://', '').replace('http://', '').split('.')[0] if SUPABASE_URL else ''
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
        f'postgresql://postgres:{os.environ.get("SUPABASE_DB_PASSWORD", "")}@db.{_supabase_host}.supabase.co:5432/postgres'
    ) if os.environ.get('DATABASE_URL') or _supabase_host else 'sqlite:///queue.db'

    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@queueapp.com')

    # SMS settings (Twilio)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

    # SocketIO
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE', '')

    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

    # QR Code
    QR_CODE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'qrcodes')

    # Password policy defaults
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_NUMBER = os.environ.get('PASSWORD_REQUIRE_NUMBER', 'true').lower() == 'true'
    PASSWORD_REQUIRE_SPECIAL = os.environ.get('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///queue.db'


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
