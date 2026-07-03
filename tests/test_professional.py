import io
import re

from app.extensions import db
from app.models.portfolio import PortfolioItem
from app.models.skill import Skill
from app.models.user import User
from app.models.verification import Verification


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


def test_dashboard_shows_profile_completion_checklist(client, category):
    register_professional(client, category)
    response = client.get("/professional/dashboard")
    assert response.status_code == 200
    assert b"Your Profile Strength" in response.data
    # A freshly registered individual professional has only the
    # "business_info" checklist item satisfied (default professional_type
    # is "individual", which needs no business name/CAC) - 1 of 12 items.
    assert b"8%" in response.data
    assert b"Upload a profile photo" in response.data


def test_profile_update_persists_availability(client, app, category):
    register_professional(client, category)

    response = client.post(
        "/professional/profile",
        data={
            "profession": "Master Electrician",
            "category_id": category,
            "city": "Lagos",
            "state": "Lagos",
            "years_experience": "5",
            "bio": "Reliable and punctual.",
            "available_days": ["Mon", "Wed", "Fri"],
            "available_hours": "8:00 AM - 6:00 PM",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Your profile has been updated" in response.data

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        profile = user.professional_profile
        assert profile.profession == "Master Electrician"
        assert profile.available_days == "Mon,Wed,Fri"
        assert profile.available_hours == "8:00 AM - 6:00 PM"

    # The GET re-render must reflect the saved days as checked checkboxes,
    # not just the correct value in the database.
    page = client.get("/professional/profile")
    html = page.data.decode()
    for day, should_be_checked in [("Mon", True), ("Tue", False), ("Wed", True), ("Fri", True), ("Sun", False)]:
        match = re.search(rf'<input[^>]*value="{day}"[^>]*>', html)
        assert match is not None, f"checkbox for {day} not found"
        assert ("checked" in match.group(0)) == should_be_checked, f"{day} checked-state mismatch"


def test_add_and_remove_skill(client, app, category):
    register_professional(client, category)

    response = client.post("/professional/skills", data={"name": "Solar Installation"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Solar Installation" in response.data

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        skill = Skill.query.filter_by(professional_profile_id=user.professional_profile.id).first()
        assert skill is not None
        skill_id = skill.id

    response = client.post(f"/professional/skills/{skill_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Skill removed" in response.data

    with app.app_context():
        assert db.session.get(Skill, skill_id) is None


def test_add_portfolio_item_without_image(client, app, category):
    register_professional(client, category)

    response = client.post(
        "/professional/portfolio",
        data={"title": "Rewired a 4-bedroom duplex", "description": "Full rewiring job in Lekki."},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Rewired a 4-bedroom duplex" in response.data

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        item = PortfolioItem.query.filter_by(professional_profile_id=user.professional_profile.id).first()
        assert item is not None
        assert item.image_filename is None


def test_add_portfolio_item_with_image(client, app, category):
    register_professional(client, category)

    fake_image = (io.BytesIO(b"\xff\xd8\xff\xe0fakejpegdata"), "photo.jpg")
    response = client.post(
        "/professional/portfolio",
        data={"title": "Panel installation", "description": "", "image": fake_image},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        item = PortfolioItem.query.filter_by(professional_profile_id=user.professional_profile.id).first()
        assert item.image_filename is not None
        assert item.image_filename.endswith(".jpg")


def test_delete_portfolio_item(client, app, category):
    register_professional(client, category)
    client.post(
        "/professional/portfolio",
        data={"title": "Sample work", "description": ""},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        item_id = PortfolioItem.query.filter_by(professional_profile_id=user.professional_profile.id).first().id

    response = client.post(f"/professional/portfolio/{item_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Portfolio item removed" in response.data

    with app.app_context():
        assert db.session.get(PortfolioItem, item_id) is None


def test_verification_upload_and_download(client, app, category):
    register_professional(client, category)

    fake_pdf = (io.BytesIO(b"%PDF-1.4 fake"), "id-card.pdf")
    response = client.post(
        "/professional/verification",
        data={"document_type": "Government ID", "file": fake_pdf},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"pending review" in response.data
    assert b"Pending" in response.data

    with app.app_context():
        user = User.query.filter_by(email="tunde@example.com").first()
        doc = Verification.query.filter_by(professional_profile_id=user.professional_profile.id).first()
        assert doc is not None
        doc_id = doc.id

    response = client.get(f"/professional/verification/{doc_id}/download")
    assert response.status_code == 200


def test_verification_download_blocked_for_other_professional(client, app, category):
    register_professional(client, category, email="owner@example.com")
    fake_pdf = (io.BytesIO(b"%PDF-1.4 fake"), "id-card.pdf")
    client.post(
        "/professional/verification",
        data={"document_type": "Government ID", "file": fake_pdf},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with app.app_context():
        owner = User.query.filter_by(email="owner@example.com").first()
        doc_id = Verification.query.filter_by(professional_profile_id=owner.professional_profile.id).first().id

    client.get("/auth/logout")
    register_professional(client, category, email="other@example.com")

    response = client.get(f"/professional/verification/{doc_id}/download")
    assert response.status_code == 404


def test_verification_rejects_unsupported_file_type(client, category):
    register_professional(client, category)

    fake_exe = (io.BytesIO(b"MZfake"), "malware.exe")
    response = client.post(
        "/professional/verification",
        data={"document_type": "Government ID", "file": fake_exe},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"Images or PDF only" in response.data
