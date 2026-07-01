from app.extensions import db
from app.models.booking import Booking
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


def register_customer(client, email="jane@example.com"):
    return client.post(
        "/auth/register/customer",
        data={
            "full_name": "Jane Doe",
            "email": email,
            "phone": "08012345678",
            "city": "Lagos",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )


def register_professional(client, category_id, email="tunde@example.com"):
    return client.post(
        "/auth/register/professional",
        data={
            "full_name": "Tunde Bello",
            "email": email,
            "phone": "08099999999",
            "profession": "Electrician",
            "category_id": category_id,
            "city": "Abuja",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )


def _login(client, email, password="supersecret"):
    client.get("/auth/logout")
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _create_accepted_booking(client, app, category_id):
    register_professional(client, category_id)
    with app.app_context():
        professional_user_id = User.query.filter_by(email="tunde@example.com").first().id

    client.get("/auth/logout")
    register_customer(client)
    client.post(
        f"/customer/book/{professional_user_id}",
        data={
            "title": "Fix wiring",
            "description": "Kitchen socket is sparking.",
            "location": "Lagos",
            "budget_naira": "10000",
            "preferred_date": "",
        },
        follow_redirects=True,
    )

    with app.app_context():
        booking = Booking.query.order_by(Booking.id.desc()).first()
        booking_id = booking.id

    _login(client, "tunde@example.com")
    client.post(f"/professional/bookings/{booking_id}/accept", follow_redirects=True)

    return booking_id


def test_cannot_start_conversation_before_booking_accepted(client, app, category):
    register_professional(client, category)
    with app.app_context():
        professional_user_id = User.query.filter_by(email="tunde@example.com").first().id

    client.get("/auth/logout")
    register_customer(client)
    client.post(
        f"/customer/book/{professional_user_id}",
        data={
            "title": "Fix wiring",
            "description": "Kitchen socket is sparking.",
            "location": "Lagos",
            "budget_naira": "10000",
            "preferred_date": "",
        },
        follow_redirects=True,
    )
    with app.app_context():
        booking_id = Booking.query.order_by(Booking.id.desc()).first().id

    response = client.get(f"/messages/start/{booking_id}")
    assert response.status_code == 400


def test_conversation_created_after_booking_accepted(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)

    response = client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        convo = Conversation.query.filter_by(booking_id=booking_id).first()
        assert convo is not None


def test_customer_and_professional_can_exchange_messages(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)

    # Professional is currently logged in (accepted the booking last).
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    response = client.post(f"/messages/{convo_id}", data={"body": "Hi, when works for you?"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Hi, when works" in response.data

    _login(client, "jane@example.com")
    response = client.get(f"/messages/{convo_id}")
    assert b"Hi, when works" in response.data

    response = client.post(f"/messages/{convo_id}", data={"body": "Tomorrow morning works."}, follow_redirects=True)
    assert b"Tomorrow morning works" in response.data

    with app.app_context():
        messages = Message.query.filter_by(conversation_id=convo_id).order_by(Message.id).all()
        assert len(messages) == 2
        assert messages[0].body == "Hi, when works for you?"
        assert messages[1].body == "Tomorrow morning works."


def test_viewing_conversation_marks_messages_read(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    client.post(f"/messages/{convo_id}", data={"body": "Hello from the professional"})

    _login(client, "jane@example.com")
    with app.app_context():
        unread_before = Message.query.filter_by(conversation_id=convo_id, is_read=False).count()
        assert unread_before == 1

    client.get(f"/messages/{convo_id}")

    with app.app_context():
        unread_after = Message.query.filter_by(conversation_id=convo_id, is_read=False).count()
        assert unread_after == 0


def test_new_message_creates_notification(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    client.post(f"/messages/{convo_id}", data={"body": "Hello from the professional"})

    _login(client, "jane@example.com")
    response = client.get("/notifications/")
    assert b"New message from Tunde Bello" in response.data


def test_conversations_list_shows_unread_count(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    client.post(f"/messages/{convo_id}", data={"body": "Hello from the professional"})

    _login(client, "jane@example.com")
    response = client.get("/messages/")
    assert b"Tunde Bello" in response.data
    assert b"Fix wiring" in response.data


def test_third_party_cannot_view_conversation(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    client.get("/auth/logout")
    register_professional(client, category, email="other@example.com")

    response = client.get(f"/messages/{convo_id}")
    assert response.status_code == 404


def test_poll_endpoint_returns_only_newer_messages(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    client.post(f"/messages/{convo_id}", data={"body": "First message"})

    with app.app_context():
        first_id = Message.query.filter_by(conversation_id=convo_id).first().id

    client.post(f"/messages/{convo_id}", data={"body": "Second message"})

    response = client.get(f"/messages/{convo_id}/poll?since={first_id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["body"] == "Second message"


def test_unread_message_badge_appears_in_navbar(client, app, category):
    booking_id = _create_accepted_booking(client, app, category)
    client.get(f"/messages/start/{booking_id}", follow_redirects=True)
    with app.app_context():
        convo_id = Conversation.query.filter_by(booking_id=booking_id).first().id

    client.post(f"/messages/{convo_id}", data={"body": "Hello from the professional"})

    _login(client, "jane@example.com")
    response = client.get("/customer/dashboard")
    html = response.data.decode()
    assert "Unread Messages" in html
    assert 'class="mt-2 text-3xl font-extrabold text-brand-900">1<' in html
