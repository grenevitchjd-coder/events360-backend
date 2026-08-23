"""
Sends email via SendGrid's SMTP relay — the same provider (and delivery
method) the original Rails EventNXT app used. Credentials come from env
vars, auto-populated if you add the SendGrid add-on on Heroku.
"""

import smtplib
from email.mime.text import MIMEText

from app.config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.sendgrid_username or not settings.sendgrid_password:
        # No credentials configured (e.g. local dev without the add-on) —
        # log instead of failing, so the rest of the app keeps working.
        print(f"[email not sent — no SendGrid credentials configured] To: {to} | Subject: {subject}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    with smtplib.SMTP("smtp.sendgrid.net", 587) as server:
        server.starttls()
        server.login(settings.sendgrid_username, settings.sendgrid_password)
        server.sendmail(settings.email_from, [to], msg.as_string())