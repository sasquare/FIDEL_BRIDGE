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


def test_dashboard_shows_category_shortcuts(client, category):
    register_customer(client)
    response = client.get("/customer/dashboard")
    assert response.status_code == 200
    assert b"Browse by Category" in response.data


def test_profile_page_prefills_existing_data(client):
    register_customer(client)
    response = client.get("/customer/profile")
    assert response.status_code == 200
    assert b"Jane Doe" in response.data
    assert b"Lagos" in response.data


def test_profile_update_persists_changes(client, app):
    register_customer(client)

    response = client.post(
        "/customer/profile",
        data={
            "full_name": "Jane Smith",
            "phone": "08099990000",
            "address": "12 Marina Road",
            "city": "Abuja",
            "state": "FCT",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Your profile has been updated" in response.data

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        assert user.full_name == "Jane Smith"
        assert user.customer_profile.city == "Abuja"
        assert user.customer_profile.state == "FCT"
