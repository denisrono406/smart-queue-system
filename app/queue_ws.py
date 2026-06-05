from flask import Blueprint
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app.extensions import socketio, db
from app.models import Ticket, ServiceDesk, Notification

queue_ws = Blueprint('queue_ws', __name__)


def emit_queue_update(desk_id, org_id):
    desk = db.session.get(ServiceDesk, desk_id)
    if not desk:
        return

    waiting = Ticket.query.filter_by(
        service_desk_id=desk_id, status='waiting'
    ).order_by(Ticket.joined_at).all()

    if desk.organization and desk.organization.enable_priority_queue:
        waiting.sort(key=lambda t: t.priority_order)

    current_serving = Ticket.query.filter(
        Ticket.service_desk_id == desk_id,
        Ticket.status.in_(['called', 'serving'])
    ).first()

    queue_data = {
        'desk_id': desk_id,
        'desk_name': desk.name,
        'org_id': org_id,
        'current_serving': current_serving.to_dict() if current_serving else None,
        'waiting_count': len(waiting),
        'waiting_tickets': [t.to_dict() for t in waiting[:20]],
    }

    socketio.emit('queue_update', queue_data, room=f'desk_{desk_id}')
    socketio.emit('queue_update', queue_data, room=f'org_{org_id}')


def emit_ticket_called(ticket):
    socketio.emit('ticket_called', {
        'ticket_id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'desk_name': ticket.service_desk.name if ticket.service_desk else '',
        'user_id': ticket.user_id,
        'message': f'Your turn! Please proceed to {ticket.service_desk.name}.',
    }, room=f'user_{ticket.user_id}')


def emit_position_update(ticket):
    socketio.emit('position_update', {
        'ticket_id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'position': ticket.queue_position,
        'estimated_wait_minutes': ticket.estimated_wait_minutes,
    }, room=f'user_{ticket.user_id}')


@socketio.on('join_desk_room')
def on_join_desk_room(data):
    desk_id = data.get('desk_id')
    if desk_id:
        join_room(f'desk_{desk_id}')


@socketio.on('leave_desk_room')
def on_leave_desk_room(data):
    desk_id = data.get('desk_id')
    if desk_id:
        leave_room(f'desk_{desk_id}')


@socketio.on('join_org_room')
def on_join_org_room(data):
    org_id = data.get('org_id')
    if org_id:
        join_room(f'org_{org_id}')


@socketio.on('join_user_room')
def on_join_user_room(data):
    user_id = data.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')


@socketio.on('leave_user_room')
def on_leave_user_room(data):
    user_id = data.get('user_id')
    if user_id:
        leave_room(f'user_{user_id}')


@socketio.on('request_queue_status')
def on_request_queue_status(data):
    desk_id = data.get('desk_id')
    if desk_id:
        emit_queue_update(desk_id, data.get('org_id', ''))
