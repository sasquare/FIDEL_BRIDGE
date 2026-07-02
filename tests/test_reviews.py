from app.extensions import db
from app.models.booking import Booking
from app.models.review import Review
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


def register_professional(client, category_id, email="tunde@example.com", city="Abuja"):
    return client.post(
        "/auth/register/professional",
        data={
            "full_name": "Tunde Bello",
            "email": email,
            "phone": "08099999999",
            "profession": "Electrician",
            "category_id": category_id,
            "city": city,
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )


def _login(client, email, password="supersecret"):
    client.get("/auth/logout")
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _complete_booking(client, app, category_id, professional_email="tunde@example.com", customer_email="jane@example.com"):
    client.get("/auth/logout")
    register_professional(client, category_id, email=professional_email)
    with app.app_context():
        professional_user_id = User.query.filter_by(email=professional_email).first().id

    client.get("/auth/logout")
    register_customer(client, email=customer_email)
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

    _login(client, professional_email)
    client.post(f"/professional/bookings/{booking_id}/accept")
    client.post(f"/professional/bookings/{booking_id}/start")
    client.post(f"/professional/bookings/{booking_id}/complete")

    _login(client, customer_email)
    return booking_id


def test_customer_can_leave_review_after_completion(client, app, category):
    booking_id = _complete_booking(client, app, category)

    response = client.post(
        f"/customer/bookings/{booking_id}/review",
        data={"rating": "5", "comment": "Excellent work, very professional."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Thanks for your review" in response.data

    with app.app_context():
        review = Review.query.filter_by(booking_id=booking_id).first()
        assert review is not None
        assert review.rating == 5
        assert review.comment == "Excellent work, very professional."


def test_cannot_review_before_completion(client, app, category):
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

    response = client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "5", "comment": ""})
    assert response.status_code == 400


def test_cannot_review_same_booking_twice(client, app, category):
    booking_id = _complete_booking(client, app, category)
    client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "5", "comment": "Great!"})

    response = client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "3", "comment": "Actually just okay."})
    assert response.status_code == 400

    with app.app_context():
        reviews = Review.query.filter_by(booking_id=booking_id).all()
        assert len(reviews) == 1
        assert reviews[0].rating == 5


def test_review_appears_on_public_profile_and_updates_average(client, app, category):
    booking_id = _complete_booking(client, app, category)
    client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "4", "comment": "Solid job."})

    with app.app_context():
        professional_user_id = User.query.filter_by(email="tunde@example.com").first().id

    response = client.get(f"/browse/professionals/{professional_user_id}")
    assert b"Solid job." in response.data
    assert b"4.0 (1)" in response.data


def test_review_notification_sent_to_professional(client, app, category):
    booking_id = _complete_booking(client, app, category)
    client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "5", "comment": "Great!"})

    _login(client, "tunde@example.com")
    response = client.get("/notifications/")
    assert b"5-star review" in response.data


def test_search_filters_by_minimum_rating(client, app, category):
    booking_id = _complete_booking(client, app, category, professional_email="five@example.com", customer_email="c1@example.com")
    client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "5", "comment": ""})

    booking_id_2 = _complete_booking(
        client, app, category, professional_email="two@example.com", customer_email="c2@example.com"
    )
    client.post(f"/customer/bookings/{booking_id_2}/review", data={"rating": "2", "comment": ""})

    with app.app_context():
        five_star_user = User.query.filter_by(email="five@example.com").first()
        two_star_user = User.query.filter_by(email="two@example.com").first()

    response = client.get("/browse/professionals?min_rating=4")
    html = response.data.decode()
    assert f"/browse/professionals/{five_star_user.id}" in html
    assert f"/browse/professionals/{two_star_user.id}" not in html


def test_search_sort_by_highest_rated(client, app, category):
    booking_id = _complete_booking(client, app, category, professional_email="low@example.com", customer_email="c1@example.com")
    client.post(f"/customer/bookings/{booking_id}/review", data={"rating": "2", "comment": ""})

    booking_id_2 = _complete_booking(client, app, category, professional_email="high@example.com", customer_email="c2@example.com")
    client.post(f"/customer/bookings/{booking_id_2}/review", data={"rating": "5", "comment": ""})

    response = client.get("/browse/professionals?sort=rating")
    html = response.data.decode()

    with app.app_context():
        low_user = User.query.filter_by(email="low@example.com").first()
        high_user = User.query.filter_by(email="high@example.com").first()

    low_pos = html.find(f"/browse/professionals/{low_user.id}")
    high_pos = html.find(f"/browse/professionals/{high_user.id}")
    assert high_pos != -1 and low_pos != -1
    assert high_pos < low_pos


def test_search_filters_by_state(client, app, category):
    register_professional(client, category, email="lagos@example.com", city="Lagos")
    with app.app_context():
        prof = User.query.filter_by(email="lagos@example.com").first()
        prof.professional_profile.state = "Lagos State"
        db.session.commit()

    client.get("/auth/logout")
    register_professional(client, category, email="abuja@example.com", city="Abuja")
    with app.app_context():
        prof = User.query.filter_by(email="abuja@example.com").first()
        prof.professional_profile.state = "FCT"
        db.session.commit()

    response = client.get("/browse/professionals?state=Lagos")
    html = response.data.decode()
    with app.app_context():
        lagos_user = User.query.filter_by(email="lagos@example.com").first()
        abuja_user = User.query.filter_by(email="abuja@example.com").first()
    assert f"/browse/professionals/{lagos_user.id}" in html
    assert f"/browse/professionals/{abuja_user.id}" not in html
