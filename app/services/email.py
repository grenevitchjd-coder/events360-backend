# events360-backend/app/services/email.py
"""
Sends email via a generic SMTP relay, configured entirely through env vars
(SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / EMAIL_FROM) so the
provider is swappable without a code change — the same pattern EventNXT uses.
Currently pointed at Resend: host smtp.resend.com, username "resend",
password = a Resend API key. The sending domain (events360.app) must be
verified in Resend, which it already is from the EventNXT setup.
"""

import smtplib
from email.mime.text import MIMEText
from email.utils import parseaddr

from app.config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Returns True once the message is accepted by the SMTP relay. Returns
    False when no SMTP credentials are configured (e.g. local dev) — the
    message is logged instead so the rest of the app keeps working. Real
    SMTP failures RAISE (smtplib.SMTPException / OSError): callers that
    promise delivery to the user must catch and surface the cause, never
    swallow it.
    """
    if not settings.smtp_host or not settings.smtp_password:
        print(f"[email not sent — no SMTP credentials configured] To: {to} | Subject: {subject}")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    # EMAIL_FROM may carry a display name ("Events360 <no-reply@...>") —
    # the SMTP envelope sender must be the bare address.
    envelope_from = parseaddr(settings.email_from)[1] or settings.email_from

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(envelope_from, [to], msg.as_string())
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(envelope_from, [to], msg.as_string())
    return True