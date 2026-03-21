import logging
import smtplib
from email.message import EmailMessage
from threading import Thread

from flask import current_app


logger = logging.getLogger(__name__)


def _build_message(cfg, email, gym_name, token, role):
    frontend_url = (cfg.get("FRONTEND_URL") or "http://localhost:3000").rstrip("/")
    invite_link = f"{frontend_url}/accept-invite?token={token}"

    if role == "trainer":
        subject = f"You've been invited to manage {gym_name}"
        role_line = f"You have been invited to manage the gym \"{gym_name}\" as a trainer."
    else:
        subject = f"You've been invited to join {gym_name}"
        role_line = f"You have been invited to join the gym \"{gym_name}\" as a member."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_DEFAULT_SENDER"]
    msg["To"] = email
    msg.set_content(
        f"""
Hello,

{role_line}

To activate your account and set your password, click the link below:
{invite_link}

This invite link expires in 24 hours.

If you did not expect this invitation, you can safely ignore this email.

- Gym Platform Team
""".strip()
    )
    return msg


def _send_email(cfg, email, gym_name, token, role):
    msg = _build_message(cfg, email, gym_name, token, role)
    timeout = int(cfg.get("MAIL_TIMEOUT") or 8)

    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=timeout) as server:
        server.starttls()
        server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        server.send_message(msg)


def _send_email_safely(cfg, email, gym_name, token, role):
    try:
        _send_email(cfg, email, gym_name, token, role)
    except Exception:
        logger.exception("Failed to send invite email to %s", email)


def send_gymadmin_invite_email(email, gym_name, token, role="client", async_send=True):
    cfg = {
        "FRONTEND_URL": current_app.config.get("FRONTEND_URL"),
        "MAIL_SERVER": current_app.config.get("MAIL_SERVER"),
        "MAIL_PORT": current_app.config.get("MAIL_PORT"),
        "MAIL_USERNAME": current_app.config.get("MAIL_USERNAME"),
        "MAIL_PASSWORD": current_app.config.get("MAIL_PASSWORD"),
        "MAIL_DEFAULT_SENDER": current_app.config.get("MAIL_DEFAULT_SENDER"),
        "MAIL_TIMEOUT": current_app.config.get("MAIL_TIMEOUT", 8),
    }

    if async_send:
        thread = Thread(
            target=_send_email_safely,
            args=(cfg, email, gym_name, token, role),
            daemon=True,
        )
        thread.start()
        return True

    _send_email(cfg, email, gym_name, token, role)
    return True
