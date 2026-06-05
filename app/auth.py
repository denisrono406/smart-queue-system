import uuid
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Role, Organization, Notification
from app.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import hash_password, check_password, validate_password, send_email_notification
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

auth_bp = Blueprint('auth', __name__)

serializer = None


def get_serializer():
    global serializer
    if serializer is None:
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        login_id = form.login_id.data.strip()
        password = form.password.data
        remember = form.remember.data

        user = User.query.filter((User.email == login_id) | (User.phone == login_id)).first()

        if user and check_password(password, user.password_hash):
            if not user.is_active:
                flash('Your account has been deactivated. Contact administrator.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=remember)
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()

            next_page = request.args.get('next')
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid login credentials. Please try again.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()

    orgs = Organization.query.filter_by(is_active=True).all()
    form.organization_id.choices = [('', '-- Select Organization (Optional) --')] + [
        (org.id, org.name) for org in orgs
    ]

    if form.validate_on_submit():
        # Check if email/phone already exists
        if form.email.data and User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html', form=form)
        if form.phone.data and User.query.filter_by(phone=form.phone.data).first():
            flash('Phone number already registered.', 'danger')
            return render_template('auth/register.html', form=form)

        customer_role = Role.query.filter_by(name='customer').first()
        if not customer_role:
            Role.insert_roles()
            customer_role = Role.query.filter_by(name='customer').first()

        org_id = form.organization_id.data if form.organization_id.data else None

        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data if form.email.data else None,
            phone=form.phone.data if form.phone.data else None,
            password_hash=hash_password(form.password.data),
            role_id=customer_role.id,
            organization_id=org_id,
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Registration successful! Welcome to Smart Queue.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        login_id = form.login_id.data.strip()
        user = User.query.filter((User.email == login_id) | (User.phone == login_id)).first()

        if user:
            s = get_serializer()
            token = s.dumps(user.id, salt='password-reset')

            if user.email:
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                html = render_template('auth/email/reset_password.html', reset_url=reset_url, user=user)
                send_email_notification(user.email, 'Password Reset Request', html)
                flash('Password reset link sent to your email.', 'success')
            elif user.phone:
                # Generate OTP for phone
                otp = str(uuid.uuid4().int)[:6]
                # Store OTP temporarily
                from app.models import Setting
                Setting.set_setting(user.id, 'auth', 'reset_otp', otp)
                Setting.set_setting(user.id, 'auth', 'reset_otp_expiry',
                                    str(int(datetime.now(timezone.utc).timestamp()) + 600))
                flash('OTP sent to your phone number. Enter it to reset your password.', 'info')
                return redirect(url_for('auth.reset_password_otp', user_id=user.id))
        else:
            flash('No account found with that email or phone.', 'warning')

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm()
    try:
        s = get_serializer()
        user_id = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('The reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    except BadSignature:
        flash('Invalid reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if form.validate_on_submit():
        errors = validate_password(form.password.data, user.organization_id)
        if errors:
            for e in errors:
                flash(e, 'danger')
        else:
            user.password_hash = hash_password(form.password.data)
            db.session.commit()
            flash('Password has been reset. You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form, token=token)


@auth_bp.route('/reset-password-otp/<user_id>', methods=['GET', 'POST'])
def reset_password_otp(user_id):
    form = ResetPasswordForm()
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        otp = request.form.get('otp', '')
        from app.models import Setting
        stored_otp = Setting.get_setting(user.id, 'auth', 'reset_otp', '')
        if otp != stored_otp:
            flash('Invalid OTP.', 'danger')
            return render_template('auth/reset_password_otp.html', form=form, user_id=user_id)

        errors = validate_password(form.password.data, user.organization_id)
        if errors:
            for e in errors:
                flash(e, 'danger')
        else:
            user.password_hash = hash_password(form.password.data)
            db.session.commit()
            flash('Password has been reset. You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_otp.html', form=form, user_id=user_id)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
