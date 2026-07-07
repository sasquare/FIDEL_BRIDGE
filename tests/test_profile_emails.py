from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.extensions import db
from app.models.notification import Notification
from app.models.portfolio import PortfolioItem
from app.models.skill import Skill
from app.models.user import User
from app.models.verification import Verification
from app.utils.profile_emails import (
    CONGRATS_SUBJECT,
    REMINDER_SUBJECT,
    WELCOME_SUBJECT,
    _completion_tone,
    maybe_send_completion_congrats,
    run_due_reminders,
    send_welcome_email,
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


def _complete_all_checklist_items_except_skills(professional):
    """Sets every profile-completion checklist item directly except
    skills, so a test can drive the real /professional/skills route to
    observe the exact moment completion crosses to 100%."""
    professional.profile_photo_filename = "1/photo.png"
    professional.bio = "A reliable electrician with a decade of experience."
    professional.years_experience = 10
    professional.city = "Abuja"
    professional.state = "FCT"
    professional.available_days = "Mon,Tue,Wed"
    professional.available_hours = "9am - 5pm"
    professional.pricing_type = "hourly"
    professional.pricing_amount = 5000
    professional.guarantor_name = "Ade Ade"
    professional.guarantor_phone = "08011111111"
    professional.emergency_contact_name = "Bisi Bello"
    professional.emergency_contact_phone = "08022222222"
    db.session.add(
        PortfolioItem(professional_profile_id=professional.id, title="Panel install", description="")
    )
    db.session.add(
        Verification(professional_profile_id=professional.id, document_type="Government ID", filename="1/id.png")
    )
    db.session.commit()


# ---------------------------------------------------------------------------
# Welcome email
# ---------------------------------------------------------------------------


def test_welcome_email_sent_once_after_registration(client, app, category):
    with patch("app.utils.profile_emails.send_email") as mock_send:
        register_professional(client, category)

    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "tunde@example.com"
    assert args[1] == WELCOME_SUBJECT
    assert kwargs["html_body"] is not None

    with app.app_context():
        professional = User.query.filter_by(email="tunde@example.com").first().professional_profile
        assert professional.welcome_email_sent_at is not None


def test_welcome_email_is_not_sent_twice(app, category):
    # test_request_context (not a bare app_context): rendering the email
    # templates goes through the app's context processors, which reference
    # flask_login's current_user - that needs an active request context.
    with app.test_request_context():
        register_professional_user = User(full_name="Tunde Bello", email="tunde2@example.com", role="professional")
        register_professional_user.set_password("supersecret")
        from app.models.professional import ProfessionalProfile

        register_professional_user.professional_profile = ProfessionalProfile(
            profession="Electrician", category_id=category, city="Abuja"
        )
        db.session.add(register_professional_user)
        db.session.commit()
        professional = register_professional_user.professional_profile

        with patch("app.utils.profile_emails.send_email") as mock_send:
            send_welcome_email(professional)
            send_welcome_email(professional)

        assert mock_send.call_count == 1


def test_registration_succeeds_even_if_welcome_email_send_fails(client, app, category):
    with patch("app.utils.profile_emails.send_email", side_effect=RuntimeError("SMTP down")):
        response = register_professional(client, category)

    assert response.status_code == 200
    assert b"Your professional account has been created" in response.data

    with app.app_context():
        assert User.query.filter_by(email="tunde@example.com").first() is not None


# ---------------------------------------------------------------------------
# Adaptive reminder tone
# ---------------------------------------------------------------------------


def test_completion_tone_bands():
    assert "great start" in _completion_tone(0)
    assert "great start" in _completion_tone(30)
    assert "good progress" in _completion_tone(31)
    assert "good progress" in _completion_tone(70)
    assert "almost there" in _completion_tone(71)
    assert "almost there" in _completion_tone(99)


def test_reminder_email_lists_only_incomplete_checklist_items(app, category):
    with app.test_request_context():
        register_professional_user = User(full_name="Tunde Bello", email="tunde3@example.com", role="professional")
        register_professional_user.set_password("supersecret")
        from app.models.professional import ProfessionalProfile

        register_professional_user.professional_profile = ProfessionalProfile(
            profession="Electrician", category_id=category, city="Abuja"
        )
        db.session.add(register_professional_user)
        db.session.commit()
        professional = register_professional_user.professional_profile
        professional.bio = "Reliable and experienced."
        db.session.add(Skill(professional_profile_id=professional.id, name="Wiring"))
        db.session.commit()

        with patch("app.utils.profile_emails.send_email") as mock_send:
            from app.utils.profile_emails import send_profile_completion_reminder

            send_profile_completion_reminder(professional, stage=1)

        args, kwargs = mock_send.call_args
        text_body = args[2]
        assert "Write a short bio" not in text_body
        assert "Add at least one skill" not in text_body
        assert "Upload a profile photo" in text_body
        assert professional.profile_reminder_stage == 1
        assert professional.profile_reminder_sent_at is not None


# ---------------------------------------------------------------------------
# Reminder scheduling
# ---------------------------------------------------------------------------


def _register_bare_professional(app, category, email="tunde4@example.com", days_ago=0):
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        user = User(full_name="Tunde Bello", email=email, role="professional")
        user.set_password("supersecret")
        user.professional_profile = ProfessionalProfile(profession="Electrician", category_id=category, city="Abuja")
        db.session.add(user)
        db.session.commit()
        professional = user.professional_profile
        professional.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        db.session.commit()
        return professional.id


def test_run_due_reminders_sends_stage_1_after_3_days_not_before(app, category):
    professional_id = _register_bare_professional(app, category, days_ago=2)

    with app.app_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        sent = run_due_reminders()
    assert sent == 0
    mock_send.assert_not_called()

    professional_id = _register_bare_professional(app, category, email="tunde5@example.com", days_ago=3)
    with app.app_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        sent = run_due_reminders()
    assert sent == 1
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[1] == REMINDER_SUBJECT

    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.profile_reminder_stage == 1


def test_run_due_reminders_never_sends_duplicate_for_same_stage(app, category):
    _register_bare_professional(app, category, days_ago=5)

    with app.app_context(), patch("app.utils.profile_emails.send_email"):
        first_run = run_due_reminders()
        second_run = run_due_reminders()

    assert first_run == 1
    assert second_run == 0


def test_run_due_reminders_skips_while_profile_is_100_percent_complete(app, category):
    professional_id = _register_bare_professional(app, category, days_ago=10)
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        _complete_all_checklist_items_except_skills(professional)
        db.session.add(Skill(professional_profile_id=professional.id, name="Wiring"))
        db.session.commit()
        assert professional.profile_completion_percentage == 100

    with app.app_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        sent = run_due_reminders()

    assert sent == 0
    mock_send.assert_not_called()
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.profile_reminder_stage == 0


def test_run_due_reminders_resumes_if_completion_drops_below_100_before_exhausted(app, category):
    """A professional who was 100% complete on day 3 (stage 1 skipped, not
    advanced) and then removes something before day 7 should still get the
    stage-1 reminder - the schedule pauses while complete, it doesn't lose
    the slot forever."""
    professional_id = _register_bare_professional(app, category, days_ago=3)
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        _complete_all_checklist_items_except_skills(professional)
        db.session.add(Skill(professional_profile_id=professional.id, name="Wiring"))
        db.session.commit()
        assert professional.profile_completion_percentage == 100

    with app.app_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        sent = run_due_reminders()
    assert sent == 0
    mock_send.assert_not_called()
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.profile_reminder_stage == 0
        # Drop below 100% and fast-forward past the day-7 checkpoint too.
        professional.bio = None
        professional.created_at = datetime.now(timezone.utc) - timedelta(days=7)
        db.session.commit()

    with app.app_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        sent = run_due_reminders()

    assert sent == 1
    mock_send.assert_called_once()
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        # It's the stage-1 (never-sent) reminder that fires, not stage 2 -
        # the schedule doesn't skip ahead just because more days passed.
        assert professional.profile_reminder_stage == 1


def test_run_due_reminders_stops_permanently_after_final_stage(app, category):
    professional_id = _register_bare_professional(app, category, days_ago=30)
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        professional.profile_reminder_stage = 3
        db.session.commit()

    with app.app_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        sent = run_due_reminders()

    assert sent == 0
    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# One-time completion congratulations
# ---------------------------------------------------------------------------


def test_congrats_email_and_notification_sent_when_crossing_to_100_percent(client, app, category):
    register_professional(client, category)

    with app.app_context():
        professional = User.query.filter_by(email="tunde@example.com").first().professional_profile
        _complete_all_checklist_items_except_skills(professional)
        assert professional.profile_completion_percentage < 100
        professional_id = professional.id

    with patch("app.utils.profile_emails.send_email") as mock_send:
        response = client.post(
            "/professional/skills", data={"name": "Wiring"}, follow_redirects=True
        )
    assert response.status_code == 200

    congrats_calls = [call for call in mock_send.call_args_list if call.args[1] == CONGRATS_SUBJECT]
    assert len(congrats_calls) == 1

    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        assert professional.profile_completion_percentage == 100
        assert professional.profile_completion_congrats_sent_at is not None

        notification = Notification.query.filter_by(user_id=professional.user_id).first()
        assert notification is not None
        assert "complete" in notification.message.lower()


def test_congrats_email_never_sent_twice_even_after_dropping_below_100_and_recompleting(app, category):
    professional_id = _register_bare_professional(app, category, days_ago=0)
    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        _complete_all_checklist_items_except_skills(professional)
        db.session.add(Skill(professional_profile_id=professional.id, name="Wiring"))
        db.session.commit()
        assert professional.profile_completion_percentage == 100

    with app.test_request_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        maybe_send_completion_congrats(professional)
        db.session.commit()
    assert mock_send.call_count == 1

    with app.app_context():
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        # Drop back below 100%, then complete again.
        professional.bio = None
        db.session.commit()
        assert professional.profile_completion_percentage < 100
        professional.bio = "Reliable and experienced."
        db.session.commit()
        assert professional.profile_completion_percentage == 100

    with app.test_request_context(), patch("app.utils.profile_emails.send_email") as mock_send:
        from app.models.professional import ProfessionalProfile

        professional = db.session.get(ProfessionalProfile, professional_id)
        maybe_send_completion_congrats(professional)
        db.session.commit()
    mock_send.assert_not_called()
