from flask import current_app
import smtplib
from email.message import EmailMessage


def send_gymadmin_invite_email(email, gym_name, token, role="client"):
    cfg = current_app.config

    invite_link = f"{cfg['FRONTEND_URL']}/accept-invite?token={token}"

    # Role-aware subject & message
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

    msg.set_content(f"""
Hello,

{role_line}

To activate your account and set your password, click the link below:
{invite_link}

⚠️ This invite link expires in 24 hours.

If you did not expect this invitation, you can safely ignore this email.

— Gym Platform Team
""".strip())

    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as server:
        server.starttls()
        server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        server.send_message(msg)
