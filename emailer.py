"""Email sender utility for shortlisted candidates."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from config import settings

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE = """Hi {candidate_name},

Congratulations! Based on our screening, your profile has been shortlisted for the next round.

Our team will contact you soon with further details.

Best regards,
{sender_name}
"""


def send_shortlist_email(
    to_email: str,
    candidate_name: str,
    subject: str = "Application Update: Shortlisted",
    template: str = DEFAULT_TEMPLATE,
) -> None:
    """Send a single shortlist email via SMTP."""
    if not settings.email_username or not settings.email_password:
        raise RuntimeError("EMAIL_USERNAME or EMAIL_PASSWORD is missing in environment")

    body = template.format(candidate_name=candidate_name, sender_name=settings.sender_name)
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = formataddr((settings.sender_name, settings.email_username))
    message["To"] = to_email

    logger.debug("Connecting to SMTP server %s:%s", settings.smtp_host, settings.smtp_port)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.email_username, settings.email_password)
        smtp.sendmail(settings.email_username, [to_email], message.as_string())

    logger.info("Shortlist email sent to %s", to_email)


def notify_shortlisted_candidates(shortlisted: list[dict]) -> dict[str, int]:
    """Send emails to all shortlisted candidates and return summary counts."""
    sent = 0
    failed = 0

    for candidate in shortlisted:
        email = candidate.get("email", "").strip()
        name = candidate.get("candidate_name", "Candidate")

        if not email:
            logger.warning("Skipping %s: no email found in resume", name)
            failed += 1
            continue

        try:
            send_shortlist_email(to_email=email, candidate_name=name)
            sent += 1
        except Exception as error:
            logger.exception("Failed to send email to %s (%s): %s", name, email, error)
            failed += 1

    return {"sent": sent, "failed": failed}
