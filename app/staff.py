from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (User, Role, Organization, ServiceDesk, Ticket,
                         Notification, Setting)
from app.utils import (calculate_estimated_wait, send_email_notification,
                        send_sms_notification)

staff_bp = Blueprint('staff', __name__)


def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff():
            flash('Access denied. Staff privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


@staff_bp.route('/dashboard')
@login_required
@staff_required
def desk_dashboard():
    org = current_user.organization
    if not org:
        flash('You are not assigned to an organization.', 'danger')
        return redirect(url_for('main.index'))

    desks = ServiceDesk.query.filter_by(organization_id=org.id, is_active=True).all()

    # Get current serving tickets for each desk
    desk_info = []
    for desk in desks:
        current_ticket = Ticket.query.filter_by(
            service_desk_id=desk.id,
            status='serving'
        ).first()
        called_ticket = Ticket.query.filter_by(
            service_desk_id=desk.id,
            status='called'
        ).first()

        active_ticket = current_ticket or called_ticket

        waiting_count = Ticket.query.filter_by(
            service_desk_id=desk.id,
            status='waiting'
        ).count()

        desk_info.append({
            'desk': desk,
            'active_ticket': active_ticket,
            'waiting_count': waiting_count
        })

    return render_template('staff/dashboard.html', desk_info=desk_info)


@staff_bp.route('/desk/<desk_id>')
@login_required
@staff_required
def view_desk(desk_id):
    desk = db.session.get(ServiceDesk, desk_id)
    if not desk or str(desk.organization_id) != str(current_user.organization_id):
        flash('Desk not found.', 'danger')
        return redirect(url_for('staff.desk_dashboard'))

    current_ticket = Ticket.query.filter_by(
        service_desk_id=desk.id,
        status='serving'
    ).first()
    if not current_ticket:
        current_ticket = Ticket.query.filter_by(
            service_desk_id=desk.id,
            status='called'
        ).first()

    waiting_tickets = Ticket.query.filter_by(
        service_desk_id=desk.id,
        status='waiting'
    ).order_by(Ticket.joined_at).all()

    # Calculate statistics
    today = datetime.now(timezone.utc).date()
    completed_today = Ticket.query.filter(
        Ticket.service_desk_id == desk.id,
        Ticket.status == 'completed',
        db.func.date(Ticket.joined_at) == today
    ).count()

    org = desk.organization

    return render_template(
        'staff/desk_view.html',
        desk=desk,
        current_ticket=current_ticket,
        waiting_tickets=waiting_tickets,
        completed_today=completed_today,
        org=org
    )


@staff_bp.route('/desk/<desk_id>/call-next', methods=['POST'])
@login_required
@staff_required
def call_next(desk_id):
    desk = db.session.get(ServiceDesk, desk_id)
    if not desk or str(desk.organization_id) != str(current_user.organization_id):
        return jsonify({'error': 'Desk not found'}), 404

    # Check if there's already an active ticket
    active = Ticket.query.filter(
        Ticket.service_desk_id == desk.id,
        Ticket.status.in_(['called', 'serving'])
    ).first()
    if active:
        print("ACTIVE TICKET:",active.id, active.status)
        return jsonify({'error': 'Finish current ticket first'}), 400

    # Get next ticket in queue (FIFO)
    next_ticket = Ticket.query.filter_by(
        service_desk_id=desk.id,
        status='waiting'
    ).order_by(Ticket.joined_at).first()

    if not next_ticket:
        print("NO WAITING TICKETS FOUND")
        return jsonify({'error': 'No tickets in queue'}), 404

    next_ticket.status = 'called'
    next_ticket.called_at = datetime.now(timezone.utc)
    db.session.commit()

    # Notify users about their updated queue position
    notify_queue_updates(desk.id)

    return jsonify({
        'success': True,
        'ticket_number': next_ticket.ticket_number,
        'user_name': next_ticket.user.full_name
    })
    

@staff_bp.route('/desk/<desk_id>/call-priority/<priority>', methods=['POST'])
@login_required
@staff_required
def call_priority(desk_id, priority):
    desk = db.session.get(ServiceDesk, desk_id)
    if not desk or str(desk.organization_id) != str(current_user.organization_id):
        return jsonify({'error': 'Desk not found'}), 404

    # Check if there's already an active ticket running on this desk
    active = Ticket.query.filter(
        Ticket.service_desk_id == desk.id,
        Ticket.status.in_(['called', 'serving'])
    ).first()
    if active:
        return jsonify({'error': 'Finish current ticket first'}), 400

    # Clean priority keyword argument (e.g., 'pwd' -> 'PWD') to match DB records
    target_priority = str(priority).strip().upper()

    # Query for matching tickets with case insensitivity handled via .upper()
    next_ticket = Ticket.query.filter(
        Ticket.service_desk_id == desk.id,
        Ticket.status == 'waiting',
        db.func.upper(Ticket.priority) == target_priority
    ).order_by(Ticket.joined_at).first()

    if not next_ticket:
        return jsonify({'error': f'No tickets found with priority: {target_priority}'}), 404

    next_ticket.status = 'called'
    next_ticket.called_at = datetime.now(timezone.utc)
    db.session.commit()

    # Notify remaining queue elements about adjustments
    notify_queue_updates(desk.id)

    return jsonify({
        'success': True,
        'ticket_number': next_ticket.ticket_number,
        'user_name': next_ticket.user.full_name
    })


@staff_bp.route('/desk/<desk_id>/start-serving/<ticket_id>', methods=['POST'])
@login_required
@staff_required
def start_serving(desk_id, ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or str(ticket.service_desk_id) != str(desk_id):
        return jsonify({'error': 'Ticket not found'}), 404

    ticket.status = 'serving'
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({'success': True})


@staff_bp.route('/desk/<desk_id>/complete/<ticket_id>', methods=['POST'])
@login_required
@staff_required
def complete_ticket(desk_id, ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or str(ticket.service_desk_id) != str(desk_id):
        return jsonify({'error': 'Ticket not found'}), 404

    ticket.status = 'completed'
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    notify_queue_updates(desk_id)

    return jsonify({'success': True})


@staff_bp.route('/desk/<desk_id>/no-show/<ticket_id>', methods=['POST'])
@login_required
@staff_required
def mark_no_show(desk_id, ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or str(ticket.service_desk_id) != str(desk_id):
        return jsonify({'error': 'Ticket not found'}), 404

    ticket.status = 'no_show'
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    notify_queue_updates(desk_id)

    return jsonify({'success': True})


def notify_queue_updates(desk_id):
    """Recalculates waiting numbers and dispatches notifications to users remaining in line."""
    waiting_tickets = Ticket.query.filter_by(
        service_desk_id=desk_id,
        status='waiting'
    ).order_by(Ticket.joined_at).all()

    desk = db.session.get(ServiceDesk, desk_id)
    org = desk.organization if desk else None

    for index, ticket in enumerate(waiting_tickets):
        # Update dynamic runtime properties if available
        ticket.queue_position = index + 1
        ticket.estimated_wait = calculate_estimated_wait(desk_id, ticket.queue_position)

        # Notify user when they are within proximity thresholds (e.g., top 3)
        if ticket.queue_position <= 3 and org:
            message = (
                f"Your turn is approaching.\n"
                f"Only {ticket.queue_position} people remain ahead of you.\n"
                f"Please proceed to the service desk."
            )

            # Check if reminder already sent recently
            existing = Notification.query.filter_by(
                user_id=ticket.user_id,
                ticket_id=ticket.id,
                type='queue_reminder'
            ).first()
            if not existing:
                notification = Notification(
                    user_id=ticket.user_id,
                    organization_id=org.id,
                    ticket_id=ticket.id,
                    type='queue_reminder',
                    channel='in_app',
                    title='Queue Reminder',
                    message=message,
                )
                db.session.add(notification)

                if Setting.get_setting(org.id, 'notification', 'email_enabled', 'true') == 'true' and ticket.user.email:
                    send_email_notification(
                        ticket.user.email,
                        f'Queue Reminder - {ticket.ticket_number}',
                        f"<p>{message.replace(chr(10), '<br>')}</p>",
                        message
                    )
                if Setting.get_setting(org.id, 'notification', 'sms_enabled', 'false') == 'true' and ticket.user.phone:
                    send_sms_notification(ticket.user.phone, message)

    db.session.commit()