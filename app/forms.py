from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SelectField, TextAreaField,
                     BooleanField, IntegerField, TimeField, EmailField, TelField,
                     FileField, DateField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo,
                                 Optional, ValidationError)
from app.utils import validate_password


class LoginForm(FlaskForm):
    login_id = StringField('Email or Phone', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')


class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = TelField('Phone Number', validators=[Optional(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    organization_id = SelectField('Organization', validators=[Optional()])

    def validate(self, extra_validators=None):
        rv = super().validate(extra_validators)
        if not rv:
            return False
        if not self.email.data and not self.phone.data:
            self.email.errors.append('Either email or phone number is required.')
            self.phone.errors.append('Either email or phone number is required.')
            return False
        return True

    def validate_password(self, field):
        errors = validate_password(field.data)
        if errors:
            raise ValidationError(errors[0])


class ForgotPasswordForm(FlaskForm):
    login_id = StringField('Email or Phone', validators=[DataRequired()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])


class OrganizationForm(FlaskForm):
    name = StringField('Organization Name', validators=[DataRequired(), Length(max=200)])
    org_type = SelectField('Organization Type', validators=[DataRequired()], choices=[
        ('school', 'School'), ('university', 'University'), ('college', 'College'),
        ('hospital', 'Hospital'), ('bank', 'Bank'), ('government', 'Government Office'),
        ('sacco', 'SACCO'), ('insurance', 'Insurance Company'), ('ngo', 'NGO'),
        ('utility', 'Utility Company'), ('other', 'Other'),
    ])
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = TelField('Phone', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    working_hours_start = TimeField('Working Hours Start', validators=[Optional()])
    working_hours_end = TimeField('Working Hours End', validators=[Optional()])
    max_queue_size = IntegerField('Max Queue Size', default=100)
    ticket_prefix = StringField('Ticket Prefix', validators=[Optional(), Length(max=10)])
    avg_service_time_minutes = IntegerField('Avg Service Time (minutes)', default=5)
    enable_priority_queue = BooleanField('Enable Priority Queue', default=True)
    enable_qr_code = BooleanField('Enable QR Code', default=True)
    reminder_threshold = IntegerField('Reminder Threshold (people ahead)', default=2)


class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])


class ServiceDeskForm(FlaskForm):
    name = StringField('Desk Name', validators=[DataRequired(), Length(max=200)])
    prefix = StringField('Ticket Prefix (3 chars)', validators=[DataRequired(), Length(min=1, max=10)])
    department_id = SelectField('Department', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    desk_number = IntegerField('Desk Number', default=1)


class StaffForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = TelField('Phone', validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired()])
    service_desk_id = SelectField('Assigned Desk', validators=[Optional()])


class JoinQueueForm(FlaskForm):
    organization_id = SelectField('Organization', validators=[DataRequired()])
    service_desk_id = SelectField('Service Desk', validators=[DataRequired()])
    priority = SelectField('Priority', validators=[DataRequired()], choices=[
        ('normal', 'Normal'), ('emergency', 'Emergency'),
        ('pwd', 'Persons with Disabilities'), ('pregnant', 'Pregnant Women'),
        ('senior', 'Senior Citizens'), ('vip', 'VIP'),
    ], default='normal')


class SettingsForm(FlaskForm):
    # Auth settings
    password_min_length = IntegerField('Min Password Length', default=8)
    password_require_uppercase = BooleanField('Require Uppercase', default=True)
    password_require_lowercase = BooleanField('Require Lowercase', default=True)
    password_require_number = BooleanField('Require Number', default=True)
    password_require_special = BooleanField('Require Special Character', default=True)

    # Queue settings
    max_queue_size = IntegerField('Max Queue Size', default=100)
    avg_service_time = IntegerField('Avg Service Time (min)', default=5)
    reminder_threshold = IntegerField('Reminder Threshold', default=2)

    # Notification settings
    email_notifications = BooleanField('Enable Email Notifications', default=True)
    sms_notifications = BooleanField('Enable SMS Notifications', default=False)

    # Ticket settings
    enable_qr_code = BooleanField('Enable QR Code', default=True)
    ticket_prefix = StringField('Ticket Prefix', validators=[Optional(), Length(max=10)])
    enable_priority_queue = BooleanField('Enable Priority Queue', default=True)


class ReportForm(FlaskForm):
    report_type = SelectField('Report Type', validators=[DataRequired()], choices=[
        ('daily', 'Daily Report'), ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'), ('desk_performance', 'Desk Performance'),
        ('queue_performance', 'Queue Performance'),
    ])
    date_from = DateField('From Date', validators=[DataRequired()])
    date_to = DateField('To Date', validators=[DataRequired()])
    file_format = SelectField('Format', choices=[
        ('pdf', 'PDF'), ('excel', 'Excel'),
    ], default='pdf')
    service_desk_id = SelectField('Service Desk', validators=[Optional()])
