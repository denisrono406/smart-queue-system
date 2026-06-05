import re
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (User, Role, Organization, Department, ServiceDesk,
                         Ticket, Notification, Setting, Report)
from app.forms import (OrganizationForm, DepartmentForm, ServiceDeskForm,
                        StaffForm, SettingsForm)
from app.utils import hash_password, validate_password

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_org():
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def super_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super_admin():
            flash('Access denied. Super Admin privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


# ── Super Admin Routes ──────────────────────────────────────

@admin_bp.route('/super-admin/dashboard')
@login_required
@super_admin_required
def super_admin_dashboard():
    total_orgs = Organization.query.count()
    active_orgs = Organization.query.filter_by(is_active=True).count()
    total_users = User.query.count()
    total_tickets_today = Ticket.query.filter(
        db.func.date(Ticket.joined_at) == datetime.now(timezone.utc).date()
    ).count()
    completed_today = Ticket.query.filter(
        db.func.date(Ticket.completed_at) == datetime.now(timezone.utc).date(),
        Ticket.status == 'completed'
    ).count()

    recent_orgs = Organization.query.order_by(Organization.created_at.desc()).limit(5).all()

    return render_template('admin/super_dashboard.html',
                           total_orgs=total_orgs, active_orgs=active_orgs,
                           total_users=total_users, total_tickets_today=total_tickets_today,
                           completed_today=completed_today, recent_orgs=recent_orgs)


@admin_bp.route('/super-admin/organizations')
@login_required
@super_admin_required
def list_organizations():
    orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    return render_template('admin/list_organizations.html', organizations=orgs)


@admin_bp.route('/super-admin/organizations/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_organization():
    form = OrganizationForm()
    if form.validate_on_submit():
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', form.name.data.lower()).strip('-')

        existing = Organization.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{Organization.query.count() + 1}"

        org = Organization(
            name=form.name.data,
            org_type=form.org_type.data,
            slug=slug,
            email=form.email.data or '',
            phone=form.phone.data or '',
            address=form.address.data or '',
            working_hours_start=form.working_hours_start.data,
            working_hours_end=form.working_hours_end.data,
            max_queue_size=form.max_queue_size.data or 100,
            ticket_prefix=form.ticket_prefix.data or '',
            avg_service_time_minutes=form.avg_service_time_minutes.data or 5,
            enable_priority_queue=form.enable_priority_queue.data,
            enable_qr_code=form.enable_qr_code.data,
            reminder_threshold=form.reminder_threshold.data or 2,
        )
        db.session.add(org)
        db.session.commit()

        # Initialize default settings
        for cat, key, val in [
            ('auth', 'password_min_length', '8'),
            ('auth', 'password_require_uppercase', 'true'),
            ('auth', 'password_require_lowercase', 'true'),
            ('auth', 'password_require_number', 'true'),
            ('auth', 'password_require_special', 'true'),
            ('notification', 'email_enabled', 'true'),
            ('notification', 'sms_enabled', 'false'),
            ('queue', 'max_queue_size', str(form.max_queue_size.data or 100)),
            ('queue', 'avg_service_time_minutes', str(form.avg_service_time_minutes.data or 5)),
            ('queue', 'reminder_threshold', str(form.reminder_threshold.data or 2)),
            ('ticket', 'enable_qr_code', str(form.enable_qr_code.data).lower()),
            ('ticket', 'enable_priority_queue', str(form.enable_priority_queue.data).lower()),
        ]:
            Setting.set_setting(org.id, cat, key, val)

        flash(f'Organization "{org.name}" created successfully.', 'success')
        return redirect(url_for('admin.list_organizations'))

    return render_template('admin/create_organization.html', form=form)


@admin_bp.route('/super-admin/organizations/<org_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_organization(org_id):
    org = db.session.get(Organization, org_id)
    if not org:
        flash('Organization not found.', 'danger')
        return redirect(url_for('admin.list_organizations'))

    form = OrganizationForm(obj=org)
    if form.validate_on_submit():
        org.name = form.name.data
        org.org_type = form.org_type.data
        org.email = form.email.data or ''
        org.phone = form.phone.data or ''
        org.address = form.address.data or ''
        org.working_hours_start = form.working_hours_start.data
        org.working_hours_end = form.working_hours_end.data
        org.max_queue_size = form.max_queue_size.data or 100
        org.ticket_prefix = form.ticket_prefix.data or ''
        org.avg_service_time_minutes = form.avg_service_time_minutes.data or 5
        org.enable_priority_queue = form.enable_priority_queue.data
        org.enable_qr_code = form.enable_qr_code.data
        org.reminder_threshold = form.reminder_threshold.data or 2
        org.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        flash(f'Organization "{org.name}" updated.', 'success')
        return redirect(url_for('admin.list_organizations'))

    return render_template('admin/edit_organization.html', form=form, org=org)


@admin_bp.route('/super-admin/organizations/<org_id>/toggle-active', methods=['POST'])
@login_required
@super_admin_required
def toggle_org_active(org_id):
    org = db.session.get(Organization, org_id)
    if not org:
        flash('Organization not found.', 'danger')
        return redirect(url_for('admin.list_organizations'))
    org.is_active = not org.is_active
    org.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    status = 'activated' if org.is_active else 'deactivated'
    flash(f'Organization "{org.name}" {status}.', 'success')
    return redirect(url_for('admin.list_organizations'))


# ── Org Admin Routes ────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
@admin_required
def org_admin_dashboard():
    org = current_user.organization
    if not org:
        flash('You are not assigned to an organization.', 'danger')
        return redirect(url_for('main.index'))

    total_users = User.query.filter_by(organization_id=org.id).count()
    active_desks = ServiceDesk.query.filter_by(organization_id=org.id, is_active=True).count()
    tickets_today = Ticket.query.filter(
        Ticket.organization_id == org.id,
        db.func.date(Ticket.joined_at) == datetime.now(timezone.utc).date()
    ).all()
    served_today = [t for t in tickets_today if t.status == 'completed']
    waiting_today = [t for t in tickets_today if t.status == 'waiting']
    active_tickets = Ticket.query.filter(
        Ticket.organization_id == org.id,
        Ticket.status.in_(['waiting', 'called', 'serving'])
    ).all()

    avg_wait = 0
    completed_with_times = [t for t in served_today if t.served_at and t.joined_at]
    if completed_with_times:
        total_wait = sum((t.served_at - t.joined_at).total_seconds() / 60 for t in completed_with_times)
        avg_wait = round(total_wait / len(completed_with_times), 1)

    return render_template('admin/org_dashboard.html',
                           org=org, total_users=total_users,
                           active_desks=active_desks,
                           tickets_served_today=len(served_today),
                           pending_tickets=len(waiting_today),
                           active_queues=len(active_tickets),
                           avg_wait_time=avg_wait)


# ── Department Management ───────────────────────────────────

@admin_bp.route('/departments')
@login_required
@admin_required
def list_departments():
    org = current_user.organization
    departments = Department.query.filter_by(organization_id=org.id).all()
    return render_template('admin/list_departments.html', departments=departments, org=org)


@admin_bp.route('/departments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        org = current_user.organization
        dept = Department(
            organization_id=org.id,
            name=form.name.data,
            description=form.description.data or '',
        )
        db.session.add(dept)
        db.session.commit()
        flash(f'Department "{dept.name}" created.', 'success')
        return redirect(url_for('admin.list_departments'))
    return render_template('admin/create_department.html', form=form)


@admin_bp.route('/departments/<dept_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(dept_id):
    dept = db.session.get(Department, dept_id)
    if not dept or str(dept.organization_id) != str(current_user.organization_id):
        flash('Department not found.', 'danger')
        return redirect(url_for('admin.list_departments'))

    form = DepartmentForm(obj=dept)
    if form.validate_on_submit():
        dept.name = form.name.data
        dept.description = form.description.data or ''
        dept.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'Department "{dept.name}" updated.', 'success')
        return redirect(url_for('admin.list_departments'))
    return render_template('admin/edit_department.html', form=form, dept=dept)


@admin_bp.route('/departments/<dept_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_department(dept_id):
    dept = db.session.get(Department, dept_id)
    if not dept or str(dept.organization_id) != str(current_user.organization_id):
        flash('Department not found.', 'danger')
        return redirect(url_for('admin.list_departments'))

    if dept.service_desks.count() > 0:
        flash('Cannot delete department with active service desks.', 'danger')
        return redirect(url_for('admin.list_departments'))

    db.session.delete(dept)
    db.session.commit()
    flash(f'Department "{dept.name}" deleted.', 'success')
    return redirect(url_for('admin.list_departments'))


# ── Service Desk Management ─────────────────────────────────

@admin_bp.route('/service-desks')
@login_required
@admin_required
def list_service_desks():
    org = current_user.organization
    desks = ServiceDesk.query.filter_by(organization_id=org.id).all()
    return render_template('admin/list_service_desks.html', desks=desks, org=org)


@admin_bp.route('/service-desks/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_service_desk():
    org = current_user.organization
    form = ServiceDeskForm()

    departments = Department.query.filter_by(organization_id=org.id).all()
    form.department_id.choices = [('', '-- No Department --')] + [
        (d.id, d.name) for d in departments
    ]

    if form.validate_on_submit():
        prefix = form.prefix.data.upper().strip()
        existing = ServiceDesk.query.filter_by(organization_id=org.id, prefix=prefix).first()
        if existing:
            flash(f'Prefix "{prefix}" is already in use by desk "{existing.name}".', 'danger')
            return render_template('admin/create_service_desk.html', form=form)

        desk = ServiceDesk(
            organization_id=org.id,
            department_id=form.department_id.data or None,
            name=form.name.data,
            prefix=prefix,
            description=form.description.data or '',
            desk_number=form.desk_number.data or 1,
        )
        db.session.add(desk)
        db.session.commit()
        flash(f'Service desk "{desk.name}" created with prefix "{desk.prefix}".', 'success')
        return redirect(url_for('admin.list_service_desks'))

    return render_template('admin/create_service_desk.html', form=form)


@admin_bp.route('/service-desks/<desk_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_service_desk(desk_id):
    desk = db.session.get(ServiceDesk, desk_id)
    if not desk or str(desk.organization_id) != str(current_user.organization_id):
        flash('Service desk not found.', 'danger')
        return redirect(url_for('admin.list_service_desks'))

    org = current_user.organization
    form = ServiceDeskForm(obj=desk)
    departments = Department.query.filter_by(organization_id=org.id).all()
    form.department_id.choices = [('', '-- No Department --')] + [
        (d.id, d.name) for d in departments
    ]

    if form.validate_on_submit():
        prefix = form.prefix.data.upper().strip()
        if prefix != desk.prefix:
            existing = ServiceDesk.query.filter_by(organization_id=org.id, prefix=prefix).first()
            if existing:
                flash(f'Prefix "{prefix}" already in use.', 'danger')
                return render_template('admin/edit_service_desk.html', form=form, desk=desk)

        desk.name = form.name.data
        desk.prefix = prefix
        desk.department_id = form.department_id.data or None
        desk.description = form.description.data or ''
        desk.desk_number = form.desk_number.data or 1
        desk.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'Service desk "{desk.name}" updated.', 'success')
        return redirect(url_for('admin.list_service_desks'))

    return render_template('admin/edit_service_desk.html', form=form, desk=desk)


@admin_bp.route('/service-desks/<desk_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_service_desk(desk_id):
    desk = db.session.get(ServiceDesk, desk_id)
    if not desk or str(desk.organization_id) != str(current_user.organization_id):
        flash('Service desk not found.', 'danger')
        return redirect(url_for('admin.list_service_desks'))

    active_tickets = Ticket.query.filter(
        Ticket.service_desk_id == desk.id,
        Ticket.status.in_(['waiting', 'called', 'serving'])
    ).count()
    if active_tickets > 0:
        flash('Cannot delete desk with active tickets.', 'danger')
        return redirect(url_for('admin.list_service_desks'))

    desk.is_active = False
    db.session.commit()
    flash(f'Service desk "{desk.name}" deactivated.', 'success')
    return redirect(url_for('admin.list_service_desks'))


# ── Staff Management ────────────────────────────────────────

@admin_bp.route('/staff')
@login_required
@admin_required
def list_staff():
    org = current_user.organization
    staff_role = Role.query.filter_by(name='staff').first()
    staff_members = User.query.filter_by(
        organization_id=org.id, role_id=staff_role.id
    ).all() if staff_role else []
    return render_template('admin/list_staff.html', staff_members=staff_members, org=org)


@admin_bp.route('/staff/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_staff():
    org = current_user.organization
    form = StaffForm()

    desks = ServiceDesk.query.filter_by(organization_id=org.id, is_active=True).all()
    form.service_desk_id.choices = [('', '-- No Assigned Desk --')] + [
        (d.id, d.name) for d in desks
    ]

    if form.validate_on_submit():
        if form.email.data and User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/create_staff.html', form=form)
        if form.phone.data and User.query.filter_by(phone=form.phone.data).first():
            flash('Phone number already registered.', 'danger')
            return render_template('admin/create_staff.html', form=form)

        errors = validate_password(form.password.data, org.id)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/create_staff.html', form=form)

        staff_role = Role.query.filter_by(name='staff').first()

        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data or None,
            phone=form.phone.data or None,
            password_hash=hash_password(form.password.data),
            role_id=staff_role.id,
            organization_id=org.id,
        )
        db.session.add(user)
        db.session.commit()

        flash(f'Staff member "{user.full_name}" created.', 'success')
        return redirect(url_for('admin.list_staff'))

    return render_template('admin/create_staff.html', form=form)


@admin_bp.route('/staff/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_staff(user_id):
    user = db.session.get(User, user_id)
    if not user or str(user.organization_id) != str(current_user.organization_id):
        flash('Staff member not found.', 'danger')
        return redirect(url_for('admin.list_staff'))
    if not user.is_staff():
        flash('User is not a staff member.', 'danger')
        return redirect(url_for('admin.list_staff'))

    user.is_active = False
    db.session.commit()
    flash(f'Staff member "{user.full_name}" deactivated.', 'success')
    return redirect(url_for('admin.list_staff'))


# ── Settings ────────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    org = current_user.organization
    form = SettingsForm()

    if form.validate_on_submit():
        for cat, mapping in [
            ('auth', {
                'password_min_length': str(form.password_min_length.data),
                'password_require_uppercase': str(form.password_require_uppercase.data).lower(),
                'password_require_lowercase': str(form.password_require_lowercase.data).lower(),
                'password_require_number': str(form.password_require_number.data).lower(),
                'password_require_special': str(form.password_require_special.data).lower(),
            }),
            ('queue', {
                'max_queue_size': str(form.max_queue_size.data),
                'avg_service_time_minutes': str(form.avg_service_time.data),
                'reminder_threshold': str(form.reminder_threshold.data),
            }),
            ('notification', {
                'email_enabled': str(form.email_notifications.data).lower(),
                'sms_enabled': str(form.sms_notifications.data).lower(),
            }),
            ('ticket', {
                'enable_qr_code': str(form.enable_qr_code.data).lower(),
                'ticket_prefix': form.ticket_prefix.data or '',
                'enable_priority_queue': str(form.enable_priority_queue.data).lower(),
            }),
        ]:
            for key, val in mapping.items():
                Setting.set_setting(org.id, cat, key, val)

        # Update org-level settings too
        org.max_queue_size = form.max_queue_size.data or 100
        org.avg_service_time_minutes = form.avg_service_time.data or 5
        org.reminder_threshold = form.reminder_threshold.data or 2
        org.enable_qr_code = form.enable_qr_code.data
        org.enable_priority_queue = form.enable_priority_queue.data
        org.ticket_prefix = form.ticket_prefix.data or ''
        org.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))

    # Populate form with existing values
    if request.method == 'GET':
        form.password_min_length.data = int(Setting.get_setting(org.id, 'auth', 'password_min_length', '8'))
        form.password_require_uppercase.data = Setting.get_setting(org.id, 'auth', 'password_require_uppercase', 'true') == 'true'
        form.password_require_lowercase.data = Setting.get_setting(org.id, 'auth', 'password_require_lowercase', 'true') == 'true'
        form.password_require_number.data = Setting.get_setting(org.id, 'auth', 'password_require_number', 'true') == 'true'
        form.password_require_special.data = Setting.get_setting(org.id, 'auth', 'password_require_special', 'true') == 'true'
        form.max_queue_size.data = int(Setting.get_setting(org.id, 'queue', 'max_queue_size', '100'))
        form.avg_service_time.data = int(Setting.get_setting(org.id, 'queue', 'avg_service_time_minutes', '5'))
        form.reminder_threshold.data = int(Setting.get_setting(org.id, 'queue', 'reminder_threshold', '2'))
        form.email_notifications.data = Setting.get_setting(org.id, 'notification', 'email_enabled', 'true') == 'true'
        form.sms_notifications.data = Setting.get_setting(org.id, 'notification', 'sms_enabled', 'false') == 'true'
        form.enable_qr_code.data = Setting.get_setting(org.id, 'ticket', 'enable_qr_code', 'true') == 'true'
        form.ticket_prefix.data = Setting.get_setting(org.id, 'ticket', 'ticket_prefix', '')
        form.enable_priority_queue.data = Setting.get_setting(org.id, 'ticket', 'enable_priority_queue', 'true') == 'true'

    return render_template('admin/settings.html', form=form, org=org)


# ── View All Tickets ────────────────────────────────────────

@admin_bp.route('/tickets')
@login_required
@admin_required
def list_tickets():
    org = current_user.organization
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    desk_filter = request.args.get('desk', '')

    query = Ticket.query.filter_by(organization_id=org.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if desk_filter:
        query = query.filter_by(service_desk_id=desk_filter)

    tickets = query.order_by(Ticket.joined_at.desc()).paginate(page=page, per_page=20, error_out=False)
    desks = ServiceDesk.query.filter_by(organization_id=org.id).all()

    return render_template('admin/list_tickets.html', tickets=tickets, desks=desks,
                           status_filter=status_filter, desk_filter=desk_filter)
