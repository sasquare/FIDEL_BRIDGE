"""Profile Completion email campaign: a one-time welcome email sent right
after professional registration, day-3/7/14 reminder emails whose tone and
checklist adapt to the professional's current completion percentage, and a
one-time congratulations email the first time completion reaches 100%.

Built entirely on the existing app/utils/mail.py send_email() and
app/utils/notifications.py notify() - no new email-sending machinery, no
new notification machinery.
"""
from datetime import datetime, timezone

from flask import current_app, render_template, url_for

from app.extensions import db
from app.utils.best_match import as_aware_utc
from app.utils.mail import send_email
from app.utils.notifications import notify
from app.utils.profile_completion import profile_completion_checklist

WELCOME_SUBJECT = "Complete Your FidelBridge Profile & Increase Your Trust Score"
REMINDER_SUBJECT = "Complete Your FidelBridge Profile & Increase Your Trust Score"
CONGRATS_SUBJECT = "\U0001F389 Congratulations! Your FidelBridge Profile is Complete"

# stage -> days since signup at which that reminder becomes due. A
# professional's ProfessionalProfile.profile_reminder_stage only ever moves
# forward through this schedule (see run_due_reminders) - it never resets
# to a lower stage, even if their completion percentage drops back down
# after being sent a reminder or reaching 100%.
REMINDER_SCHEDULE = {1: 3, 2: 7, 3: 14}
FINAL_REMINDER_STAGE = max(REMINDER_SCHEDULE)


def _first_name(user):
    return user.full_name.split()[0]


def _cta_url(endpoint):
    """Absolute URL for an email call-to-action link. Deliberately doesn't
    use url_for(..., _external=True): that requires either an active
    request (fine for the welcome/congrats emails, which are always sent
    during a real request) or a configured SERVER_NAME (which the app
    doesn't set, to avoid Flask enforcing Host-header matching against a
    single hostname). Prefixing a plain, relative url_for() with
    APP_BASE_URL works identically whether called from a real request or
    from the reminder CLI job's borrowed request context."""
    return current_app.config["APP_BASE_URL"].rstrip("/") + url_for(endpoint)


def _completion_tone(percentage):
    if percentage <= 30:
        return "You've made a great start. Complete your profile so customers can discover and trust you."
    if percentage <= 70:
        return (
            "You're making good progress. Complete the remaining sections to improve your "
            "Trust Score and increase your visibility."
        )
    return (
        "You're almost there! Just a few more steps and your profile will be fully optimized, "
        "helping you rank higher and earn more customer trust."
    )


def _send(to, subject, text_template, html_template, context):
    text_body = render_template(text_template, **context)
    html_body = render_template(html_template, **context)
    try:
        send_email(to, subject, text_body, html_body=html_body)
    except Exception:
        # Never let a mail-provider failure propagate into the request (or
        # CLI run) that triggered it - see send_welcome_email's docstring.
        current_app.logger.exception("Failed to send %r to %s", subject, to)


def send_welcome_email(professional):
    """Sends the one-time welcome email immediately after registration.
    A no-op if already sent. Never raises - a failed send is logged, not
    propagated, so registration can never fail because of it."""
    if professional.welcome_email_sent_at is not None:
        return
    user = professional.user
    context = {
        "first_name": _first_name(user),
        "checklist_items": profile_completion_checklist(professional),
        "cta_url": _cta_url("professional.profile"),
    }
    _send(user.email, WELCOME_SUBJECT, "email/welcome.txt", "email/welcome.html", context)
    professional.welcome_email_sent_at = datetime.now(timezone.utc)


def send_profile_completion_reminder(professional, stage):
    """Sends the reminder for `stage` and advances the professional's
    reminder state. Does not check whether the stage is actually due -
    that's run_due_reminders' job."""
    user = professional.user
    percentage = professional.profile_completion_percentage
    incomplete_items = [item for item in profile_completion_checklist(professional) if not item.is_complete]
    context = {
        "first_name": _first_name(user),
        "percentage": percentage,
        "tone": _completion_tone(percentage),
        "incomplete_items": incomplete_items,
        "cta_url": _cta_url("professional.profile"),
    }
    _send(user.email, REMINDER_SUBJECT, "email/reminder.txt", "email/reminder.html", context)
    professional.profile_reminder_stage = stage
    professional.profile_reminder_sent_at = datetime.now(timezone.utc)
    notify(
        user,
        f"You're only {percentage}% complete. Finish your profile to improve your Trust Score "
        "and increase your visibility.",
        link=url_for("professional.dashboard"),
    )


def send_profile_completion_congrats(professional):
    user = professional.user
    context = {"first_name": _first_name(user)}
    _send(user.email, CONGRATS_SUBJECT, "email/congrats.txt", "email/congrats.html", context)
    professional.profile_completion_congrats_sent_at = datetime.now(timezone.utc)
    notify(
        user,
        "\U0001F389 Your profile is complete! You're now fully visible to customers.",
        link=url_for("professional.dashboard"),
    )


def maybe_send_completion_congrats(professional):
    """Call this right before committing any change that could push a
    professional's profile to 100% complete (see the call sites in
    app/blueprints/professional/routes.py: profile, pricing, accountability,
    skills, portfolio, verification - the exact 6 routes named as an
    edit_endpoint in PROFILE_COMPLETION_ITEMS). No-op unless this is
    genuinely the first time they've reached 100% - never fires twice, and
    never fires again after a later edit drops them back below 100%."""
    if professional.profile_completion_congrats_sent_at is not None:
        return
    if professional.profile_completion_percentage != 100:
        return
    send_profile_completion_congrats(professional)


def run_due_reminders():
    """Sends every profile-completion reminder that's currently due, across
    all professionals. Safe to run on any cadence (daily, hourly, or ad hoc)
    - each professional's own profile_reminder_stage is the only thing that
    decides what's due, so re-running never sends a duplicate.

    Intended to be triggered by the `flask send-profile-completion-reminders`
    CLI command on whatever external schedule you wire up (a Render Cron Job,
    a scheduled GitHub Action, or any other trigger that can invoke a
    one-off command) - this function itself has no opinion on scheduling.

    Returns the number of reminders sent.
    """
    from app.models.professional import ProfessionalProfile

    with current_app.test_request_context():
        now = datetime.now(timezone.utc)
        sent = 0
        professionals = ProfessionalProfile.query.filter(
            ProfessionalProfile.profile_reminder_stage < FINAL_REMINDER_STAGE
        ).all()
        for professional in professionals:
            if professional.profile_completion_percentage == 100:
                continue

            next_stage = professional.profile_reminder_stage + 1
            days_required = REMINDER_SCHEDULE[next_stage]
            days_since_signup = (now - as_aware_utc(professional.created_at)).days
            if days_since_signup < days_required:
                continue

            send_profile_completion_reminder(professional, next_stage)
            db.session.commit()
            sent += 1
        return sent
