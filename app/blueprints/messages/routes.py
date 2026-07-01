from datetime import datetime, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.blueprints.messages import messages_bp
from app.extensions import db
from app.forms.message import MessageForm
from app.models.booking import STATUS_ACCEPTED, STATUS_COMPLETED, STATUS_IN_PROGRESS, Booking
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.notifications import notify

# Contact between two parties only opens up once a booking has been
# accepted - matches the phone-number reveal rule from the booking system.
MESSAGING_ENABLED_STATUSES = (STATUS_ACCEPTED, STATUS_IN_PROGRESS, STATUS_COMPLETED)


def _get_own_conversation(conversation_id):
    conversation = db.get_or_404(Conversation, conversation_id)
    if not conversation.is_participant(current_user):
        abort(404)
    return conversation


def _mark_incoming_read(conversation):
    unread = [m for m in conversation.messages if m.sender_id != current_user.id and not m.is_read]
    for message in unread:
        message.is_read = True
    if unread:
        db.session.commit()


@messages_bp.route("/")
@login_required
def conversations():
    all_conversations = (
        Conversation.query.filter(
            or_(Conversation.user_one_id == current_user.id, Conversation.user_two_id == current_user.id)
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return render_template("messages/conversations.html", conversations=all_conversations)


@messages_bp.route("/start/<int:booking_id>")
@login_required
def start(booking_id):
    booking = db.get_or_404(Booking, booking_id)

    customer_user = booking.customer.user
    professional_user = booking.professional.user
    if current_user.id not in (customer_user.id, professional_user.id):
        abort(404)

    if booking.status not in MESSAGING_ENABLED_STATUSES:
        abort(400)

    conversation = Conversation.query.filter_by(booking_id=booking.id).first()
    if conversation is None:
        conversation = Conversation(
            user_one_id=customer_user.id, user_two_id=professional_user.id, booking_id=booking.id
        )
        db.session.add(conversation)
        db.session.commit()

    return redirect(url_for("messages.conversation", conversation_id=conversation.id))


@messages_bp.route("/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def conversation(conversation_id):
    convo = _get_own_conversation(conversation_id)
    form = MessageForm()

    if form.validate_on_submit():
        message = Message(conversation_id=convo.id, sender_id=current_user.id, body=form.body.data.strip())
        db.session.add(message)
        # message.created_at isn't populated until flush/insert, so set this
        # from a fresh timestamp rather than reading the (still-None) column default.
        convo.updated_at = datetime.now(timezone.utc)
        notify(
            convo.other_participant(current_user),
            f"New message from {current_user.full_name}",
            link=url_for("messages.conversation", conversation_id=convo.id),
        )
        db.session.commit()
        return redirect(url_for("messages.conversation", conversation_id=convo.id))

    _mark_incoming_read(convo)

    return render_template("messages/conversation.html", conversation=convo, form=form)


@messages_bp.route("/<int:conversation_id>/poll")
@login_required
def poll(conversation_id):
    convo = _get_own_conversation(conversation_id)
    since_id = request.args.get("since", 0, type=int)

    new_messages = [m for m in convo.messages if m.id > since_id]
    _mark_incoming_read(convo)

    return jsonify(
        [
            {
                "id": m.id,
                "body": m.body,
                "is_own": m.sender_id == current_user.id,
                "sender_name": m.sender.full_name,
                "created_at": m.created_at.strftime("%d %b, %I:%M %p"),
            }
            for m in new_messages
        ]
    )
