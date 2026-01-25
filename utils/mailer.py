from flask import current_app
import smtplib
from email.message import EmailMessage

def send_gymadmin_invite_email(email, gym_name, token):
    cfg = current_app.config

    invite_link = f"{cfg['FRONTEND_URL']}/accept-invite?token={token}"

    msg = EmailMessage()
    msg["Subject"] = f"You've been invited to manage {gym_name}"
    msg["From"] = cfg["MAIL_DEFAULT_SENDER"]
    msg["To"] = email

    msg.set_content(f"""
Hello,

You have been invited to manage the gym "{gym_name}".

Activate your account by setting your password:
{invite_link}

⚠️ This link expires in 24 hours.

— Gym Platform Team
""")

    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as server:
        server.starttls()
        server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        server.send_message(msg)
