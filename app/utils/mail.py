"""Minimal outbound email helper.

No email provider is wired up for the MVP by default. If MAIL_SERVER is
configured (see app/config.py), messages are sent over SMTP; otherwise they
are written to the app logger instead of failing, so the password-reset
flow is fully usable in development/testing without real credentials.
"""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to, subject, body, html_body=None):
    """Send a plain-text email, or a multipart text+HTML one if html_body is
    given. Callers should always pass a text body - it's the fallback every
    email client can render, and the only body used when MAIL_SERVER isn't
    configured (see below)."""
    server = current_app.config.get("MAIL_SERVER")
    if not server:
        current_app.logger.info("MAIL_SERVER not configured; logging email instead of sending.\nTo: %s\nSubject: %s\n\n%s", to, subject, body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@fidelbridge.com")
    message["To"] = to
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    port = current_app.config.get("MAIL_PORT", 587)
    with smtplib.SMTP(server, port, timeout=10) as smtp:
        if current_app.config.get("MAIL_USE_TLS", True):
            smtp.starttls()
        username = current_app.config.get("MAIL_USERNAME")
        password = current_app.config.get("MAIL_PASSWORD")
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
