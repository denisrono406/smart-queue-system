import re
import bcrypt
import qrcode
import io
import base64
from flask import current_app
from PIL import Image


def hash_password(password):
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def check_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def validate_password(password, org_id=None):
    from app.models import Setting
    errors = []

    min_length = 8
    require_upper = True
    require_lower = True
    require_number = True
    require_special = True

    if org_id:
        min_length = int(Setting.get_setting(org_id, 'auth', 'password_min_length', '8'))
        require_upper = Setting.get_setting(org_id, 'auth', 'password_require_uppercase', 'true') == 'true'
        require_lower = Setting.get_setting(org_id, 'auth', 'password_require_lowercase', 'true') == 'true'
        require_number = Setting.get_setting(org_id, 'auth', 'password_require_number', 'true') == 'true'
        require_special = Setting.get_setting(org_id, 'auth', 'password_require_special', 'true') == 'true'

    if len(password) < min_length:
        errors.append(f'Password must be at least {min_length} characters long.')
    if require_upper and not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter.')
    if require_lower and not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter.')
    if require_number and not re.search(r'\d', password):
        errors.append('Password must contain at least one number.')
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Password must contain at least one special character.')

    return errors


def generate_qr_code(data, size=200):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    img_resized = img.resize((size, size), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img_resized.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f'data:image/png;base64,{img_base64}'


def save_qr_code_file(data, filename, folder):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    filepath = os.path.join(folder, filename)
    img.save(filepath, 'PNG')
    return filepath


def generate_ticket_qr_data(ticket):
    return (
        f"TICKET:{ticket.ticket_number}\n"
        f"ORG:{ticket.organization.name}\n"
        f"DESK:{ticket.service_desk.name}\n"
        f"PRIORITY:{ticket.priority}\n"
        f"POSITION:{ticket.queue_position}\n"
        f"DATE:{ticket.joined_at.strftime('%Y-%m-%d %H:%M') if ticket.joined_at else ''}\n"
        f"USER:{ticket.user.full_name}\n"
        f"ID:{ticket.id}"
    )


def calculate_estimated_wait(service_desk_id, position, org_id=None):
    from app.models import Setting
    avg_time = 5
    if org_id:
        avg_time = int(Setting.get_setting(org_id, 'queue', 'avg_service_time_minutes', '5'))
    return position * avg_time


def send_email_notification(to, subject, body_html, body_text=''):
    from app.extensions import mail
    from flask_mail import Message
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body_text,
            html=body_html
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'Email send error: {e}')
        return False


def send_sms_notification(to_phone, message):
    try:
        account_sid = current_app.config.get('TWILIO_ACCOUNT_SID', '')
        auth_token = current_app.config.get('TWILIO_AUTH_TOKEN', '')
        from_phone = current_app.config.get('TWILIO_PHONE_NUMBER', '')

        if not account_sid or not auth_token:
            current_app.logger.warning('Twilio not configured. SMS not sent.')
            return False

        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone
        )
        return True
    except Exception as e:
        current_app.logger.error(f'SMS send error: {e}')
        return False


import os
