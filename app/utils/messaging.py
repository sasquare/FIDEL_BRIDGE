from sqlalchemy import or_

from app.models.conversation import Conversation
from app.models.message import Message


def unread_message_count(user):
    return (
        Message.query.join(Conversation)
        .filter(
            or_(Conversation.user_one_id == user.id, Conversation.user_two_id == user.id),
            Message.sender_id != user.id,
            Message.is_read.is_(False),
        )
        .count()
    )
