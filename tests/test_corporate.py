from app.extensions import db
from app.models.corporate_request import CorporateRequest
from app.models.user import User


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


def submit_request(client, request_type="procurement", title="Office chairs", **extra):
    data = {
        "request_type": request_type,
        "title": title,
        "description": "Need 20 ergonomic office chairs for our Lagos office.",
        "location": "Lagos",
        "budget_naira": "500000",
        "preferred_date": "",
    }
    data.update(extra)
    return client.post("/corporate/requests/new", data=data, follow_redirects=True)


def test_dashboard_shows_zero_state(client):
    register_corporate(client)
    response = client.get("/corporate/dashboard")
    assert response.status_code == 200
    assert b"No requests yet" in response.data


def test_profile_update_persists(client, app):
    register_corporate(client)

    response = client.post(
        "/corporate/profile",
        data={
            "company_name": "Acme Facilities Nigeria Ltd",
            "rc_number": "RC999999",
            "industry": "Janitorial",
            "address": "12 Marina Road",
            "city": "Lagos",
            "state": "Lagos",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Your company profile has been updated" in response.data

    with app.app_context():
        user = User.query.filter_by(email="ops@company.com").first()
        assert user.corporate_profile.company_name == "Acme Facilities Nigeria Ltd"
        assert user.corporate_profile.city == "Lagos"


def test_submit_request_creates_pending_request(client, app):
    register_corporate(client)

    response = submit_request(client)
    assert response.status_code == 200
    assert b"Office chairs" in response.data
    assert b"Pending" in response.data

    with app.app_context():
        user = User.query.filter_by(email="ops@company.com").first()
        req = CorporateRequest.query.filter_by(corporate_profile_id=user.corporate_profile.id).first()
        assert req is not None
        assert req.status == "pending"
        assert req.request_type == "procurement"
        assert req.budget_naira == 500000


def test_new_request_preselects_type_from_query_param(client):
    register_corporate(client)
    response = client.get("/corporate/requests/new?type=janitorial")
    assert response.status_code == 200
    assert b'<option selected value="janitorial">' in response.data


def test_dashboard_stats_reflect_requests(client):
    register_corporate(client)
    submit_request(client, title="Chairs")
    submit_request(client, title="Cleaning contract", request_type="janitorial")

    response = client.get("/corporate/dashboard")
    assert response.status_code == 200
    assert b"Chairs" in response.data
    assert b"Cleaning contract" in response.data


def test_requests_page_filters_by_status(client, app):
    register_corporate(client)
    submit_request(client, title="Chairs")

    with app.app_context():
        user = User.query.filter_by(email="ops@company.com").first()
        req = CorporateRequest.query.filter_by(corporate_profile_id=user.corporate_profile.id).first()
        req.status = "completed"
        db.session.commit()

    pending_page = client.get("/corporate/requests?status=pending")
    assert b"Chairs" not in pending_page.data

    completed_page = client.get("/corporate/requests?status=completed")
    assert b"Chairs" in completed_page.data


def test_cancel_pending_request(client, app):
    register_corporate(client)
    submit_request(client, title="Chairs")

    with app.app_context():
        user = User.query.filter_by(email="ops@company.com").first()
        req = CorporateRequest.query.filter_by(corporate_profile_id=user.corporate_profile.id).first()
        req_id = req.id

    response = client.post(f"/corporate/requests/{req_id}/cancel", follow_redirects=True)
    assert response.status_code == 200
    assert b"Request cancelled" in response.data

    with app.app_context():
        req = db.session.get(CorporateRequest, req_id)
        assert req.status == "cancelled"


def test_cannot_cancel_non_pending_request(client, app):
    register_corporate(client)
    submit_request(client, title="Chairs")

    with app.app_context():
        user = User.query.filter_by(email="ops@company.com").first()
        req = CorporateRequest.query.filter_by(corporate_profile_id=user.corporate_profile.id).first()
        req.status = "completed"
        db.session.commit()
        req_id = req.id

    response = client.post(f"/corporate/requests/{req_id}/cancel")
    assert response.status_code == 400


def test_request_detail_blocked_for_other_corporate(client, app):
    register_corporate(client, email="owner@company.com")
    submit_request(client, title="Chairs")

    with app.app_context():
        user = User.query.filter_by(email="owner@company.com").first()
        req_id = CorporateRequest.query.filter_by(corporate_profile_id=user.corporate_profile.id).first().id

    client.get("/auth/logout")
    register_corporate(client, email="other@company.com")

    response = client.get(f"/corporate/requests/{req_id}")
    assert response.status_code == 404


def test_customer_cannot_access_corporate_dashboard(client):
    client.post(
        "/auth/register/customer",
        data={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "",
            "city": "",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )
    response = client.get("/corporate/dashboard")
    assert response.status_code == 403
