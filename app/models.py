from datetime import datetime, timezone
from flask_login import UserMixin
import uuid
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = [
            ('super_admin', 'System administrator with full access'),
            ('org_admin', 'Organization administrator'),
            ('staff', 'Service desk staff member'),
            ('customer', 'Regular customer/user'),
        ]
        for name, desc in roles:
            role = Role.query.filter_by(name=name).first()
            if role is None:
                role = Role(name=name, description=desc)
                db.session.add(role)
        db.session.commit()


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    org_type = db.Column(db.String(50), nullable=False, default='other')
    slug = db.Column(db.String(100), unique=True, nullable=False)
    logo_url = db.Column(db.Text, default='')
    address = db.Column(db.Text, default='')
    email = db.Column(db.String(200), default='')
    phone = db.Column(db.String(50), default='')
    working_hours_start = db.Column(db.Time, default=None)
    working_hours_end = db.Column(db.Time, default=None)
    working_days = db.Column(db.Text, default='monday,tuesday,wednesday,thursday,friday')
    is_active = db.Column(db.Boolean, default=True)
    subscription_plan = db.Column(db.String(50), default='free')
    subscription_expires_at = db.Column(db.DateTime, default=None)
    max_queue_size = db.Column(db.Integer, default=100)
    ticket_prefix = db.Column(db.String(10), default='')
    enable_priority_queue = db.Column(db.Boolean, default=True)
    enable_qr_code = db.Column(db.Boolean, default=True)
    reminder_threshold = db.Column(db.Integer, default=2)
    avg_service_time_minutes = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    departments = db.relationship('Department', backref='organization', lazy='dynamic',
                                 cascade='all, delete-orphan')
    service_desks = db.relationship('ServiceDesk', backref='organization', lazy='dynamic',
                                    cascade='all, delete-orphan')
    users = db.relationship('User', backref='organization', lazy='dynamic')
    tickets = db.relationship('Ticket', backref='organization', lazy='dynamic')

    ORG_TYPES = {
        'school': 'School',
        'university': 'University',
        'college': 'College',
        'hospital': 'Hospital',
        'bank': 'Bank',
        'government': 'Government Office',
        'sacco': 'SACCO',
        'insurance': 'Insurance Company',
        'ngo': 'NGO',
        'utility': 'Utility Company',
        'other': 'Other',
    }

    @property
    def org_type_label(self):
        return self.ORG_TYPES.get(self.org_type, 'Other')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'org_type': self.org_type,
            'slug': self.slug,
            'is_active': self.is_active,
        }


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    auth_user_id = db.Column(db.String(36), nullable=True)
    email = db.Column(db.String(200), unique=True, nullable=True)
    phone = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False, default='')
    last_name = db.Column(db.String(100), nullable=False, default='')
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime, default=None)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    tickets = db.relationship('Ticket', backref='user', lazy='dynamic',
                              foreign_keys='Ticket.user_id')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                    cascade='all, delete-orphan')
    served_tickets = db.relationship('Ticket', backref='served_by', lazy='dynamic',
                                     foreign_keys='Ticket.served_by_staff_id')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def role_name(self):
        return self.role.name if self.role else 'unknown'

    def is_super_admin(self):
        return self.role and self.role.name == 'super_admin'

    def is_org_admin(self):
        return self.role and self.role.name == 'org_admin'

    def is_staff(self):
        return self.role and self.role.name == 'staff'

    def is_customer(self):
        return self.role and self.role.name == 'customer'

    def can_manage_org(self, org_id=None):
        if self.is_super_admin():
            return True
        if self.is_org_admin():
            if org_id is None:
                return True
            return str(self.organization_id) == str(org_id)
        return False


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    service_desks = db.relationship('ServiceDesk', backref='department', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('organization_id', 'name'),)


class ServiceDesk(db.Model):
    __tablename__ = 'service_desks'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    prefix = db.Column(db.String(10), nullable=False, default='GEN')
    description = db.Column(db.Text, default='')
    desk_number = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    current_ticket_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    tickets = db.relationship('Ticket', backref='service_desk', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('organization_id', 'prefix'),)

    def get_waiting_count(self):
        return Ticket.query.filter_by(
            service_desk_id=self.id,
            status='waiting'
        ).count()

    def get_next_ticket_number(self):
        last_ticket = Ticket.query.filter_by(
            service_desk_id=self.id
        ).order_by(Ticket.joined_at.desc()).first()
        if last_ticket:
            try:
                num = int(last_ticket.ticket_number.replace(self.prefix, ''))
                return f"{self.prefix}{str(num + 1).zfill(3)}"
            except ValueError:
                return f"{self.prefix}001"
        return f"{self.prefix}001"


class Ticket(db.Model):
    __tablename__ = 'tickets'

    PRIORITY_ORDER = {
        'emergency': 1,
        'pwd': 2,
        'pregnant': 3,
        'senior': 4,
        'vip': 5,
        'normal': 6,
    }

    PRIORITY_LABELS = {
        'emergency': 'Emergency',
        'pwd': 'Persons with Disabilities',
        'pregnant': 'Pregnant Women',
        'senior': 'Senior Citizens',
        'vip': 'VIP',
        'normal': 'Normal',
    }

    STATUS_CHOICES = ['waiting', 'called', 'serving', 'completed', 'cancelled', 'no_show']

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ticket_number = db.Column(db.String(20), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    service_desk_id = db.Column(db.String(36), db.ForeignKey('service_desks.id'), nullable=False)
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    status = db.Column(db.String(20), nullable=False, default='waiting')
    queue_position = db.Column(db.Integer, nullable=False, default=0)
    estimated_wait_minutes = db.Column(db.Integer, default=0)
    qr_code_data = db.Column(db.Text, default='')
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    called_at = db.Column(db.DateTime, default=None)
    served_at = db.Column(db.DateTime, default=None)
    completed_at = db.Column(db.DateTime, default=None)
    cancelled_at = db.Column(db.DateTime, default=None)
    served_by_staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, default='')

    __table_args__ = (db.UniqueConstraint('organization_id', 'ticket_number'),)

    @property
    def priority_order(self):
        return self.PRIORITY_ORDER.get(self.priority, 6)

    @property
    def priority_label(self):
        return self.PRIORITY_LABELS.get(self.priority, 'Normal')

    @property
    def is_active(self):
        return self.status in ('waiting', 'called', 'serving')

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'priority': self.priority,
            'priority_label': self.priority_label,
            'status': self.status,
            'queue_position': self.queue_position,
            'estimated_wait_minutes': self.estimated_wait_minutes,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'service_desk_name': self.service_desk.name if self.service_desk else '',
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False, default='info')
    channel = db.Column(db.String(20), nullable=False, default='in_app')
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime, default=None)


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False, unique=False)
    category = db.Column(db.String(50), nullable=False, default='general')
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('organization_id', 'category', 'key'),)

    @staticmethod
    def get_setting(org_id, category, key, default=''):
        setting = Setting.query.filter_by(
            organization_id=org_id, category=category, key=key
        ).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(org_id, category, key, value):
        setting = Setting.query.filter_by(
            organization_id=org_id, category=category, key=key
        ).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(
                organization_id=org_id, category=category,
                key=key, value=str(value)
            )
            db.session.add(setting)
        db.session.commit()
        return setting


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    generated_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=False)
    file_path = db.Column(db.Text, default='')
    file_format = db.Column(db.String(10), default='pdf')
    summary = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
