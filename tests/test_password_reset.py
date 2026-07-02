from datetime import datetime, timedelta, timezone

from app.extensions import db
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


def test_forgot_password_shows_generic_message_for_unknown_email(client):
    response = client.post("/auth/forgot-password", data={"email": "nobody@example.com"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"a reset link has been sent" in response.data


def test_forgot_password_generates_token_for_known_email(client, app):
    register_customer(client)
    client.get("/auth/logout")

    response = client.post("/auth/forgot-password", data={"email": "jane@example.com"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"a reset link has been sent" in response.data

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        assert user.reset_token is not None
        assert user.reset_token_expires_at is not None


def test_reset_password_with_valid_token_changes_password(client, app):
    register_customer(client)
    client.get("/auth/logout")

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        token = user.generate_reset_token()
        db.session.commit()

    response = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "newpassword1", "confirm_password": "newpassword1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Your password has been reset" in response.data

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        assert user.check_password("newpassword1")
        assert user.reset_token is None
        assert user.reset_token_expires_at is None

    # Old password no longer works; new one does.
    response = client.post(
        "/auth/login", data={"email": "jane@example.com", "password": "supersecret"}, follow_redirects=True
    )
    assert b"Incorrect email or password" in response.data

    response = client.post(
        "/auth/login", data={"email": "jane@example.com", "password": "newpassword1"}, follow_redirects=True
    )
    assert b"Welcome, Jane Doe" in response.data


def test_reset_password_with_invalid_token_redirects_with_error(client):
    response = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)
    assert response.status_code == 200
    assert b"invalid or has expired" in response.data


def test_reset_password_with_expired_token_rejected(client, app):
    register_customer(client)
    client.get("/auth/logout")

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        token = user.generate_reset_token()
        user.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()

    response = client.get(f"/auth/reset-password/{token}", follow_redirects=True)
    assert response.status_code == 200
    assert b"invalid or has expired" in response.data


def test_reset_token_is_single_use(client, app):
    register_customer(client)
    client.get("/auth/logout")

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        token = user.generate_reset_token()
        db.session.commit()

    client.post(
        f"/auth/reset-password/{token}",
        data={"password": "newpassword1", "confirm_password": "newpassword1"},
        follow_redirects=True,
    )

    # Reusing the same link a second time should no longer work.
    response = client.get(f"/auth/reset-password/{token}", follow_redirects=True)
    assert b"invalid or has expired" in response.data


def test_requesting_a_new_reset_link_invalidates_the_old_one(client, app):
    register_customer(client)
    client.get("/auth/logout")

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        old_token = user.generate_reset_token()
        db.session.commit()

    client.post("/auth/forgot-password", data={"email": "jane@example.com"}, follow_redirects=True)

    response = client.get(f"/auth/reset-password/{old_token}", follow_redirects=True)
    assert b"invalid or has expired" in response.data


def test_forgot_password_redirects_authenticated_user(client):
    register_customer(client)
    response = client.get("/auth/forgot-password", follow_redirects=True)
    assert b"Welcome, Jane Doe" in response.data
