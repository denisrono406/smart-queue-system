from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Organization, Ticket, ServiceDesk

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    organizations = Organization.query.filter_by(is_active=True).all()
    return render_template('index.html', organizations=organizations)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_super_admin():
        return redirect(url_for('admin.super_admin_dashboard'))
    elif current_user.is_org_admin():
        return redirect(url_for('admin.org_admin_dashboard'))
    elif current_user.is_staff():
        return redirect(url_for('staff.desk_dashboard'))
    else:
        return redirect(url_for('user.user_dashboard'))


@main_bp.route('/verify-ticket/<ticket_id>')
def verify_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('verify_ticket.html', ticket=ticket)


@main_bp.route('/org/<slug>')
def org_public_page(slug):
    org = Organization.query.filter_by(slug=slug, is_active=True).first_or_404()
    desks = ServiceDesk.query.filter_by(organization_id=org.id, is_active=True).all()
    return render_template('org_public.html', org=org, desks=desks)
