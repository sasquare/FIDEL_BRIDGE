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


def register_professional(client, email="tunde@example.com"):
    return client.post(
        "/auth/register/professional",
        data={
            "full_name": "Tunde Bello",
            "email": email,
            "phone": "08099999999",
            "profession": "Electrician",
            "city": "Abuja",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )


def register_corporate(client, email="ops@company.com"):
    return client.post(
        "/auth/register/corporate",
        data={
            "full_name": "Grace Ede",
            "email": email,
            "phone": "08088888888",
            "company_name": "Acme Facilities Ltd",
            "rc_number": "RC123456",
            "industry": "Facility Management",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )


def test_customer_registration_creates_user_and_logs_in(client, app):
    response = register_customer(client)
    assert response.status_code == 200
    assert b"Welcome, Jane Doe" in response.data

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        assert user is not None
        assert user.role == "customer"
        assert user.check_password("supersecret")
        assert user.customer_profile.city == "Lagos"


def test_professional_registration_creates_profile(client, app):
    response = register_professional(client)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        assert user.role == "professional"
        assert user.professional_profile.profession == "Electrician"


def test_corporate_registration_creates_profile(client, app):
    response = register_corporate(client)
    assert response.status_code == 200
    assert b"Acme Facilities Ltd" in response.data

    with app.app_context():
        user = User.query.filter_by(email="ops@company.com").first()
        assert user.role == "corporate"
        assert user.corporate_profile.company_name == "Acme Facilities Ltd"


def test_duplicate_email_is_rejected(client):
    register_customer(client, email="dupe@example.com")
    client.get("/auth/logout")

    response = register_customer(client, email="dupe@example.com")
    assert b"already exists" in response.data


def test_password_mismatch_is_rejected(client):
    response = client.post(
        "/auth/register/customer",
        data={
            "full_name": "Jane Doe",
            "email": "mismatch@example.com",
            "phone": "",
            "city": "",
            "password": "supersecret",
            "confirm_password": "different",
        },
    )
    assert response.status_code == 200
    assert b"Passwords must match" in response.data


def test_login_with_correct_credentials_redirects_to_dashboard(client):
    register_customer(client, email="login@example.com")
    client.get("/auth/logout")

    response = client.post(
        "/auth/login",
        data={"email": "login@example.com", "password": "supersecret"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Customer Dashboard" in response.data or b"Welcome, Jane Doe" in response.data


def test_login_with_wrong_password_fails(client):
    register_customer(client, email="wrongpass@example.com")
    client.get("/auth/logout")

    response = client.post(
        "/auth/login",
        data={"email": "wrongpass@example.com", "password": "notthepassword"},
    )
    assert response.status_code == 200
    assert b"Incorrect email or password" in response.data


def test_logout_clears_session(client):
    register_customer(client, email="logout@example.com")
    client.get("/auth/logout")

    response = client.get("/customer/dashboard", follow_redirects=True)
    assert b"Log in to FidelBridge" in response.data


def test_anonymous_user_redirected_to_login(client):
    response = client.get("/customer/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Log in to FidelBridge" in response.data


def test_wrong_role_gets_403(client):
    register_customer(client, email="roletest@example.com")
    response = client.get("/professional/dashboard")
    assert response.status_code == 403
