"""Email delivery via SMTP."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Config

logger = logging.getLogger(__name__)


def is_configured():
    """True when SMTP credentials have been provided."""
    return bool(Config.SMTP_USER and Config.SMTP_PASSWORD)


def send_email(to_email, subject, html_body):
    """Send an HTML email.

    Returns (ok: bool, message: str).
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = Config.MAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=30) as server:
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.MAIL_FROM, [to_email], msg.as_string())
        return True, "sent"
    except Exception as exc:  # noqa: BLE001 - report the real reason upstream
        logger.exception("Failed to send email to %s", to_email)
        return False, str(exc)
