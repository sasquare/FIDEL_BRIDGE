from app.extensions import db
from app.models.booking import Booking
from app.models.category import Category
from app.models.corporate_request import CorporateRequest
from app.models.professional import ProfessionalProfile
from app.models.user import User
from app.models.verification import Verification


def _create_admin(app, email="admin@example.com"):
    with app.app_context():
        admin = User(full_name="Fidel Admin", email=email, role="admin")
        admin.set_password("supersecret")
        db.session.add(admin)
        db.session.commit()
        return admin.id


def _login(client, email, password="supersecret"):
    client.get("/auth/logout")
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


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


def test_non_admin_cannot_access_admin_dashboard(client):
    register_customer(client)
    response = client.get("/admin/dashboard")
    assert response.status_code == 403


def test_admin_dashboard_shows_stats(client, app, category):
    _create_admin(app)
    _login(client, "admin@example.com")
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Platform Overview" in response.data


def test_admin_can_approve_professional(client, app, category):
    register_professional(client, category)
    admin_id = _create_admin(app)

    with app.app_context():
        professional = ProfessionalProfile.query.first()
        professional_id = professional.id
        assert professional.is_verified is False

    _login(client, "admin@example.com")
    response = client.post(f"/admin/professionals/{professional_id}/verify", follow_redirects=True)
    assert response.status_code == 200
    assert b"is now verified" in response.data

    with app.app_context():
        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.is_verified is True

    _login(client, "tunde@example.com")
    response = client.get("/notifications/")
    assert b"has been verified" in response.data
    assert admin_id  # keep reference tidy


def test_verify_and_unverify_professional_set_and_clear_verified_at(client, app, category):
    # verified_at anchors Best Match's cold-start boost window - it must be
    # set the moment a professional is verified and cleared if that
    # verification is later revoked, not left stale.
    register_professional(client, category)
    _create_admin(app)

    with app.app_context():
        professional_id = ProfessionalProfile.query.first().id

    _login(client, "admin@example.com")
    client.post(f"/admin/professionals/{professional_id}/verify", follow_redirects=True)

    with app.app_context():
        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.verified_at is not None

    client.post(f"/admin/professionals/{professional_id}/unverify", follow_redirects=True)

    with app.app_context():
        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.verified_at is None


def test_admin_can_approve_and_reject_verification_documents(client, app, category):
    register_professional(client, category)
    with app.app_context():
        professional = ProfessionalProfile.query.first()
        doc1 = Verification(professional_profile_id=professional.id, document_type="Government ID", filename="x/1.pdf")
        doc2 = Verification(professional_profile_id=professional.id, document_type="Proof of Address", filename="x/2.pdf")
        db.session.add_all([doc1, doc2])
        db.session.commit()
        professional_id = professional.id
        doc1_id, doc2_id = doc1.id, doc2.id

    _create_admin(app)
    _login(client, "admin@example.com")

    response = client.post(f"/admin/verifications/{doc1_id}/approve", follow_redirects=True)
    assert response.status_code == 200
    assert b"Document approved" in response.data

    response = client.post(
        f"/admin/verifications/{doc2_id}/reject", data={"admin_notes": "Blurry image"}, follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        doc1 = db.session.get(Verification, doc1_id)
        doc2 = db.session.get(Verification, doc2_id)
        assert doc1.status == "approved"
        assert doc1.reviewed_at is not None
        assert doc2.status == "rejected"
        assert doc2.admin_notes == "Blurry image"

    assert professional_id


def test_admin_can_create_and_delete_category(client, app):
    _create_admin(app)
    _login(client, "admin@example.com")

    response = client.post(
        "/admin/categories",
        data={"name": "Landscapers", "icon_path": "", "description": "Garden and lawn care."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Category created" in response.data

    with app.app_context():
        category = Category.query.filter_by(name="Landscapers").first()
        assert category is not None
        assert category.slug == "landscapers"
        category_id = category.id

    response = client.post(f"/admin/categories/{category_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Category deleted" in response.data

    with app.app_context():
        assert db.session.get(Category, category_id) is None


def test_admin_can_upload_and_replace_category_image(client, app):
    import io

    _create_admin(app)
    _login(client, "admin@example.com")

    fake_image = (io.BytesIO(b"\xff\xd8\xff\xe0fakejpegdata"), "photo.jpg")
    response = client.post(
        "/admin/categories",
        data={"name": "Landscapers", "icon_path": "", "description": "", "image": fake_image},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Category created" in response.data

    with app.app_context():
        category = Category.query.filter_by(name="Landscapers").first()
        assert category.image_filename is not None
        category_id = category.id
        old_filename = category.image_filename

    with app.test_request_context():
        category = db.session.get(Category, category_id)
        assert category.image_display_url is not None

    new_image = (io.BytesIO(b"\xff\xd8\xff\xe0newjpegdata"), "new-photo.jpg")
    response = client.post(
        f"/admin/categories/{category_id}/edit",
        data={"name": "Landscapers", "icon_path": "", "description": "", "image": new_image},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Category updated" in response.data

    with app.app_context():
        category = db.session.get(Category, category_id)
        assert category.image_filename is not None
        assert category.image_filename != old_filename
        # The old file is deleted when replaced, not left orphaned on disk.
        old_path = app.config["CATEGORY_IMAGE_UPLOAD_FOLDER"] / old_filename
        assert not old_path.exists()


def test_admin_cannot_delete_category_with_professionals(client, app, category):
    register_professional(client, category)
    _create_admin(app)
    _login(client, "admin@example.com")

    response = client.post(f"/admin/categories/{category}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"still has professionals assigned" in response.data

    with app.app_context():
        assert db.session.get(Category, category) is not None


def test_admin_can_deactivate_and_reactivate_user(client, app):
    register_customer(client)
    with app.app_context():
        customer_id = User.query.filter_by(email="jane@example.com").first().id

    _create_admin(app)
    _login(client, "admin@example.com")

    response = client.post(f"/admin/users/{customer_id}/deactivate", follow_redirects=True)
    assert response.status_code == 200
    assert b"deactivated" in response.data

    _login(client, "jane@example.com")
    with app.app_context():
        assert db.session.get(User, customer_id).is_active_account is False

    _login(client, "admin@example.com")
    response = client.post(f"/admin/users/{customer_id}/activate", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(User, customer_id).is_active_account is True


def test_admin_cannot_deactivate_another_admin(client, app):
    _create_admin(app, email="admin1@example.com")
    other_admin_id = _create_admin(app, email="admin2@example.com")

    _login(client, "admin1@example.com")
    response = client.post(f"/admin/users/{other_admin_id}/deactivate")
    assert response.status_code == 400


def test_admin_can_view_and_cancel_booking(client, app, category):
    register_professional(client, category)
    with app.app_context():
        professional_user = User.query.filter_by(email="tunde@example.com").first()
        professional_user_id = professional_user.id

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

    _create_admin(app)
    _login(client, "admin@example.com")

    response = client.get(f"/admin/bookings/{booking_id}")
    assert response.status_code == 200
    assert b"Fix wiring" in response.data

    response = client.post(f"/admin/bookings/{booking_id}/cancel", follow_redirects=True)
    assert response.status_code == 200
    assert b"Booking cancelled" in response.data

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.status == "cancelled"


def test_admin_can_update_corporate_request_status(client, app):
    register_corporate(client)
    client.post(
        "/corporate/requests/new",
        data={
            "request_type": "procurement",
            "title": "Office chairs",
            "description": "Need 20 ergonomic chairs.",
            "location": "Lagos",
            "budget_naira": "500000",
            "preferred_date": "",
        },
        follow_redirects=True,
    )
    with app.app_context():
        request_id = CorporateRequest.query.first().id

    _create_admin(app)
    _login(client, "admin@example.com")

    response = client.post(
        f"/admin/corporate-requests/{request_id}/status", data={"status": "in_progress"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Request status updated" in response.data

    with app.app_context():
        req = db.session.get(CorporateRequest, request_id)
        assert req.status == "in_progress"

    _login(client, "ops@company.com")
    response = client.get("/notifications/")
    assert b"In Progress" in response.data


def test_admin_reports_page_loads(client, app, category):
    _create_admin(app)
    _login(client, "admin@example.com")
    response = client.get("/admin/reports")
    assert response.status_code == 200
    assert b"Platform Reports" in response.data
