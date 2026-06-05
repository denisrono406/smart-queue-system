from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (User, Role, Organization, ServiceDesk, Ticket,
                         Notification, Setting, Department)
from app.forms import JoinQueueForm
from app.utils import (generate_qr_code, generate_ticket_qr_data,
                        calculate_estimated_wait, send_email_notification,
                        send_sms_notification)

user_bp = Blueprint('user', __name__)


@user_bp.route('/dashboard')
@login_required
def user_dashboard():
    active_tickets = Ticket.query.filter(
        Ticket.user_id == current_user.id,
        Ticket.status.in_(['waiting', 'called', 'serving'])
    ).order_by(Ticket.joined_at.desc()).all()

    recent_tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(
        Ticket.joined_at.desc()
    ).limit(10).all()

    organizations = Organization.query.filter_by(is_active=True).all()
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()

    return render_template('user/dashboard.html',
                           active_tickets=active_tickets,
                           recent_tickets=recent_tickets,
                           organizations=organizations,
                           unread_notifications=unread_notifications)


@user_bp.route('/join-queue', methods=['GET', 'POST'])
@login_required
def join_queue():
    form = JoinQueueForm()
    
    form.service_desk_id.choices = []

    orgs = Organization.query.filter_by(is_active=True).all()
    form.organization_id.choices = [('', '-- Select Organization --')] + [
        (org.id, org.name) for org in orgs
    ]
    
    form.service_desk_id.choices = []
    selected_org =request.form.get('organization_id') or request.args.get('org_id')
    
    if selected_org:
        desks = ServiceDesk.query.filter_by(
            organization_id=selected_org,
            is_active=True
        ).all()
        form.service_desk_id.choices = [
            (desk.id, desk.name)
            for desk in desks
        ]

    if request.method == 'GET':
        org_id = request.args.get('org_id')
        if org_id:
            form.organization_id.data = org_id

    if form.validate_on_submit():
        org = db.session.get(Organization, form.organization_id.data)
        desk = db.session.get(ServiceDesk, form.service_desk_id.data)

        if not org or not desk:
            flash('Invalid organization or service desk.', 'danger')
            return render_template('user/join_queue.html', form=form)

        # Check queue capacity
        waiting_count = Ticket.query.filter_by(
            service_desk_id=desk.id, status='waiting'
        ).count()
        if waiting_count >= org.max_queue_size:
            flash('Queue is full. Please try again later.', 'danger')
            return render_template('user/join_queue.html', form=form)

        # Check if user already has active ticket for this desk
        existing = Ticket.query.filter(
            Ticket.user_id == current_user.id,
            Ticket.service_desk_id == desk.id,
            Ticket.status.in_(['waiting', 'called', 'serving'])
        ).first()
        if existing:
            flash(f'You already have an active ticket: {existing.ticket_number}', 'warning')
            return redirect(url_for('user.ticket_detail', ticket_id=existing.id))

        # Determine priority
        priority = form.priority.data
        if not org.enable_priority_queue and priority != 'normal':
            priority = 'normal'

        # Generate ticket number
        ticket_number = desk.get_next_ticket_number()

        # Calculate position
        if priority == 'normal' or not org.enable_priority_queue:
            position = waiting_count + 1
        else:
            # Priority tickets go ahead of normal
            normal_waiting = Ticket.query.filter(
                Ticket.service_desk_id == desk.id,
                Ticket.status == 'waiting',
                Ticket.priority == 'normal'
            ).count()
            priority_ahead = Ticket.query.filter(
                Ticket.service_desk_id == desk.id,
                Ticket.status == 'waiting',
            ).count()
            position = priority_ahead + 1

        # Calculate estimated wait
        est_wait = calculate_estimated_wait(desk.id, position, org.id)

        ticket = Ticket(
            ticket_number=ticket_number,
            organization_id=org.id,
            service_desk_id=desk.id,
            department_id=desk.department_id,
            user_id=current_user.id,
            priority=priority,
            status='waiting',
            queue_position=position,
            estimated_wait_minutes=est_wait,
        )
        db.session.add(ticket)
        db.session.flush()

        # Generate QR code
        if org.enable_qr_code:
            qr_data = generate_ticket_qr_data(ticket)
            ticket.qr_code_data = generate_qr_code(qr_data)

        db.session.commit()

        # Send confirmation notification
        _send_join_notification(ticket, org, desk)

        # Emit real-time update
        from app.queue_ws import emit_queue_update
        emit_queue_update(desk.id, org.id)

        flash(f'You have joined the queue! Ticket: {ticket.ticket_number}', 'success')
        return redirect(url_for('user.ticket_detail', ticket_id=ticket.id))

    return render_template('user/join_queue.html', form=form)


def _send_join_notification(ticket, org, desk):
    user = ticket.user
    message = (
        f"You have successfully joined the {desk.name}.\n"
        f"Ticket Number: {ticket.ticket_number}\n"
        f"Position: {ticket.queue_position}\n"
        f"Estimated Wait Time: {ticket.estimated_wait_minutes} minutes."
    )

    # In-app notification
    notification = Notification(
        user_id=user.id,
        organization_id=org.id,
        ticket_id=ticket.id,
        type='queue_joined',
        channel='in_app',
        title='Queue Joined',
        message=message,
    )
    db.session.add(notification)

    # Email notification
    if Setting.get_setting(org.id, 'notification', 'email_enabled', 'true') == 'true' and user.email:
        html = render_template('user/email/queue_joined.html', ticket=ticket, desk=desk, org=org)
        send_email_notification(user.email, f'Queue Joined - {ticket.ticket_number}', html, message)

    # SMS notification
    if Setting.get_setting(org.id, 'notification', 'sms_enabled', 'false') == 'true' and user.phone:
        send_sms_notification(user.phone, message)


@user_bp.route('/ticket/<ticket_id>')
@login_required
def ticket_detail(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or str(ticket.user_id) != str(current_user.id):
        flash('Ticket not found.', 'danger')
        return redirect(url_for('user.user_dashboard'))

    # Recalculate position for waiting tickets
    if ticket.status == 'waiting':
        tickets_ahead = Ticket.query.filter(
            Ticket.service_desk_id == ticket.service_desk_id,
            Ticket.status == 'waiting',
            Ticket.joined_at < ticket.joined_at
        ).count()
        ticket.queue_position = tickets_ahead + 1
        org = ticket.organization
        ticket.estimated_wait_minutes = calculate_estimated_wait(
            ticket.service_desk_id, ticket.queue_position, org.id
        )
        db.session.commit()

    return render_template('user/ticket_detail.html', ticket=ticket)


@user_bp.route('/ticket/<ticket_id>/cancel', methods=['POST'])
@login_required
def cancel_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or str(ticket.user_id) != str(current_user.id):
        flash('Ticket not found.', 'danger')
        return redirect(url_for('user.user_dashboard'))

    if ticket.status != 'waiting':
        flash('Only waiting tickets can be cancelled.', 'warning')
        return redirect(url_for('user.ticket_detail', ticket_id=ticket.id))

    ticket.status = 'cancelled'
    ticket.cancelled_at = datetime.now(timezone.utc)
    db.session.commit()

    from app.queue_ws import emit_queue_update
    emit_queue_update(ticket.service_desk_id, ticket.organization_id)

    flash(f'Ticket {ticket.ticket_number} cancelled.', 'success')
    return redirect(url_for('user.user_dashboard'))


@user_bp.route('/ticket/<ticket_id>/download-pdf')
@login_required
def download_ticket_pdf(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or str(ticket.user_id) != str(current_user.id):
        flash('Ticket not found.', 'danger')
        return redirect(url_for('user.user_dashboard'))

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet
        import io
        import base64

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []

        org = ticket.organization
        desk = ticket.service_desk

        story.append(Paragraph(f"<b>{org.name}</b>", styles['Title']))
        story.append(Paragraph(f"Queue Ticket", styles['Heading2']))
        story.append(Spacer(1, 0.3*inch))

        ticket_data = [
            ['Ticket Number:', ticket.ticket_number],
            ['Customer:', ticket.user.full_name],
            ['Organization:', org.name],
            ['Service Desk:', desk.name],
            ['Department:', desk.department.name if desk.department else 'N/A'],
            ['Priority:', ticket.priority_label],
            ['Queue Position:', str(ticket.queue_position)],
            ['Estimated Wait:', f'{ticket.estimated_wait_minutes} minutes'],
            ['Date/Time:', ticket.joined_at.strftime('%b %d, %Y %I:%M %p') if ticket.joined_at else ''],
        ]

        table = Table(ticket_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f4f8')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a365d')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)

        # Add QR code
        if ticket.qr_code_data and org.enable_qr_code:
            story.append(Spacer(1, 0.3*inch))
            qr_data = generate_ticket_qr_data(ticket)
            qr_img = generate_qr_code(qr_data, size=150)
            # Decode base64 and add to PDF
            img_data = base64.b64decode(qr_img.split(',')[1])
            img_buffer = io.BytesIO(img_data)
            img = Image(img_buffer, width=1.5*inch, height=1.5*inch)
            story.append(Paragraph("<b>Scan to verify:</b>", styles['Normal']))
            story.append(img)

        doc.build(story)
        buffer.seek(0)

        from flask import send_file
        return send_file(buffer, as_attachment=True,
                         download_name=f'ticket_{ticket.ticket_number}.pdf',
                         mimetype='application/pdf')
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('user.ticket_detail', ticket_id=ticket.id))


@user_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.sent_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('user/notifications.html', notifications=notifications)


@user_bp.route('/notifications/<notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = db.session.get(Notification, notif_id)
    if notif and str(notif.user_id) == str(current_user.id):
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify({'success': True})


@user_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True, 'read_at': datetime.now(timezone.utc)})
    db.session.commit()
    return jsonify({'success': True})


@user_bp.route('/ticket-history')
@login_required
def ticket_history():
    page = request.args.get('page', 1, type=int)
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(
        Ticket.joined_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return render_template('user/ticket_history.html', tickets=tickets)


@user_bp.route('/api/service-desks/<org_id>')
@login_required
def get_service_desks(org_id):
    desks = ServiceDesk.query.filter_by(organization_id=org_id, is_active=True).all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'prefix': d.prefix,
        'department': d.department.name if d.department else None,
        'waiting_count': d.get_waiting_count(),
    } for d in desks])
