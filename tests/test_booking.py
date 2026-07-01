from app.extensions import db
from app.models.booking import Booking
from app.models.notification import Notification
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


def _professional_user_id(app, email="tunde@example.com"):
    with app.app_context():
        return User.query.filter_by(email=email).first().id


def submit_booking(client, professional_user_id, title="Fix kitchen sink", **extra):
    data = {
        "title": title,
        "description": "The kitchen sink has been leaking for a week.",
        "location": "Lagos",
        "budget_naira": "15000",
        "preferred_date": "",
    }
    data.update(extra)
    return client.post(f"/customer/book/{professional_user_id}", data=data, follow_redirects=True)


def _create_booking_as_customer(client, app, customer_email="jane@example.com", professional_email="tunde@example.com", category_id=None):
    register_professional(client, category_id, email=professional_email)
    professional_id = _professional_user_id(app, professional_email)
    client.get("/auth/logout")
    register_customer(client, email=customer_email)
    submit_booking(client, professional_id)

    with app.app_context():
        booking = Booking.query.order_by(Booking.id.desc()).first()
        return booking.id


def test_customer_can_send_booking_request(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "pending"
        assert booking.title == "Fix kitchen sink"

        professional_user = booking.professional.user
        note = Notification.query.filter_by(user_id=professional_user.id).first()
        assert note is not None
        assert "New job request" in note.message


def test_professional_sees_pending_request_and_can_accept(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post(
        "/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True
    )

    response = client.get("/professional/bookings")
    assert b"Fix kitchen sink" in response.data

    response = client.post(f"/professional/bookings/{booking_id}/accept", follow_redirects=True)
    assert response.status_code == 200
    assert b"Job accepted" in response.data

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "accepted"
        customer_user = booking.customer.user
        note = Notification.query.filter_by(user_id=customer_user.id).order_by(Notification.id.desc()).first()
        assert "accepted" in note.message


def test_professional_can_reject_pending_booking(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True)

    response = client.post(f"/professional/bookings/{booking_id}/reject", follow_redirects=True)
    assert response.status_code == 200
    assert b"Job declined" in response.data

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "rejected"


def test_full_booking_lifecycle_accept_start_complete(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True)

    client.post(f"/professional/bookings/{booking_id}/accept")
    client.post(f"/professional/bookings/{booking_id}/start")
    response = client.post(f"/professional/bookings/{booking_id}/complete", follow_redirects=True)
    assert b"Job marked as completed" in response.data

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "completed"


def test_cannot_accept_already_accepted_booking(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True)

    client.post(f"/professional/bookings/{booking_id}/accept")
    response = client.post(f"/professional/bookings/{booking_id}/accept")
    assert response.status_code == 400


def test_customer_can_cancel_pending_booking(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    response = client.post(f"/customer/bookings/{booking_id}/cancel", follow_redirects=True)
    assert response.status_code == 200
    assert b"Booking cancelled" in response.data

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "cancelled"


def test_customer_cannot_cancel_completed_booking(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True)
    client.post(f"/professional/bookings/{booking_id}/accept")
    client.post(f"/professional/bookings/{booking_id}/start")
    client.post(f"/professional/bookings/{booking_id}/complete")

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "jane@example.com", "password": "supersecret"}, follow_redirects=True)

    response = client.post(f"/customer/bookings/{booking_id}/cancel")
    assert response.status_code == 400


def test_other_customer_cannot_view_someone_elses_booking(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    register_customer(client, email="other@example.com")

    response = client.get(f"/customer/bookings/{booking_id}")
    assert response.status_code == 404


def test_other_professional_cannot_manage_someone_elses_booking(client, app, category):
    booking_id = _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    register_professional(client, category, email="other@example.com")

    response = client.get(f"/professional/bookings/{booking_id}")
    assert response.status_code == 404

    response = client.post(f"/professional/bookings/{booking_id}/accept")
    assert response.status_code == 404


def test_notifications_page_shows_and_marks_read(client, app, category):
    _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True)

    response = client.get("/notifications/")
    assert response.status_code == 200
    assert b"New job request" in response.data

    with app.app_context():
        professional_user = User.query.filter_by(email="tunde@example.com").first()
        note = Notification.query.filter_by(user_id=professional_user.id).first()
        assert note.is_read is False
        note_id = note.id

    client.post(f"/notifications/{note_id}/read")

    with app.app_context():
        note = db.session.get(Notification, note_id)
        assert note.is_read is True


def test_navbar_shows_unread_notification_count(client, app, category):
    _create_booking_as_customer(client, app, category_id=category)

    client.get("/auth/logout")
    client.post("/auth/login", data={"email": "tunde@example.com", "password": "supersecret"}, follow_redirects=True)

    response = client.get("/professional/dashboard")
    html = response.data.decode()
    assert "New Job Requests" in html
    # The dashboard stat card should reflect the one pending request.
    assert 'class="mt-2 text-3xl font-extrabold text-brand-900">1<' in html
